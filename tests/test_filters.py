import os
from nose.tools import assert_raises, with_setup
from django.conf import settings
from django_assets.filter import Filter, get_filter, register_filter

# TODO: Add tests for all the builtin filters.


class TestFilter:
    """Test the API ``Filter`` provides to descendants.
    """

    def test_auto_name(self):
        """Test the automatic generation of the filter name.
        """
        assert type('Foo', (Filter,), {}).name == 'foo'
        assert type('FooFilter', (Filter,), {}).name == 'foo'
        assert type('FooBarFilter', (Filter,), {}).name == 'foobar'

        assert type('Foo', (Filter,), {'name': 'custom'}).name == 'custom'
        assert type('Foo', (Filter,), {'name': None}).name == None

    def test_get_config(self):
        """Test the ``get_config`` helper.
        """
        get_config = Filter().get_config

        # For the purposes of the following tests, we use two test
        # names which we expect to be undefined in both settings
        # and environment.
        NAME = 'FOO%s' % id(object())
        NAME2 = 'FOO%s' % id(NAME)
        assert NAME != NAME2
        assert not NAME in os.environ and not NAME2 in os.environ
        assert not hasattr(settings, NAME) and not hasattr(settings, NAME2)

        try:
            # Test raising of error, and test not raising it.
            assert_raises(EnvironmentError, get_config, NAME)
            assert get_config(NAME, require=False) == None

            # Start with only the environment variable set.
            os.environ[NAME] = 'bar'
            assert get_config(NAME) == 'bar'
            assert get_config(env=NAME, setting=False) == 'bar'
            assert_raises(EnvironmentError, get_config, setting=NAME, env=False)

            # Set the value in the environment as well.
            setattr(settings, NAME, 'foo')
            # Ensure that settings take precedence.
            assert get_config(NAME) == 'foo'
            # Two different names can be supplied.
            assert not hasattr(settings, NAME2)
            assert get_config(setting=NAME2, env=NAME) == 'bar'

            # Unset the env variable, now with only the setting.
            del os.environ[NAME]
            assert get_config(NAME) == 'foo'
            assert get_config(setting=NAME, env=False) == 'foo'
            assert_raises(EnvironmentError, get_config, env=NAME)
        finally:
            if NAME in os.environ:
                del os.environ[NAME]
            # Due to the way Django's settings object works, we need
            # to access ``_wrapped`` to remove the setting.
            delattr(settings._wrapped, NAME)

    def test_equality(self):
        """Test the ``unique`` method used to determine equality.
        """
        class TestFilter(Filter):
            def unique(self):
                return getattr(self, 'token', 'bar')
        f1 = TestFilter();
        f2 = TestFilter();

        # As long as the two tokens are equal, the filters are
        # considered to be the same.
        assert f1 == f2
        f1.token = 'foo'
        assert f1 != f2
        f2.token = 'foo'
        assert f1 == f2

        # However, unique() is only per class; two different filter
        # classes will never match...
        class AnotherFilter(TestFilter):
            # ...provided they have a different name.
            name = TestFilter.name + '_2'
            def unique(self):
                return 'foo'
        g = AnotherFilter()
        assert f1 != g


def reset():
    """Reset the filter module, so that different tests don't affect
    each other.
    """
    from django_assets import filter
    filter._FILTERS = {}
    filter.load_builtin_filters()


@with_setup(reset)
def test_register_filter():
    """Test registration of custom filters.
    """
    # Needs to be a ``Filter`` subclass.
    assert_raises(ValueError, register_filter, object)

    # A name is required.
    class MyFilter(Filter):
        name = None
        def output(self, *a, **kw): pass
    assert_raises(ValueError, register_filter, MyFilter)

    # The same filter cannot be registered under multiple names.
    MyFilter.name = 'foo'
    register_filter(MyFilter)
    MyFilter.name = 'bar'
    register_filter(MyFilter)

    # But the same name cannot be registered multiple times.
    assert_raises(KeyError, register_filter, MyFilter)

    # A filter needs to have at least one of the input or output methods.
    class BrokenFilter(Filter):
        name = 'broken'
    assert_raises(TypeError, register_filter, BrokenFilter)


@with_setup(reset)
def test_get_filter():
    """Test filter resolving.
    """
    # By name - here using one of the builtins.
    assert isinstance(get_filter('jsmin'), Filter)
    assert_raises(ValueError, get_filter, 'notafilteractually')

    # By class.
    class MyFilter(Filter): pass
    assert isinstance(get_filter(MyFilter), MyFilter)
    assert_raises(ValueError, get_filter, object())

    # Passing an instance doesn't do anything.
    f = MyFilter()
    assert id(get_filter(f)) == id(f)

    # Passing a lone callable will give us a a filter back as well.
    assert hasattr(get_filter(lambda: None), 'output')
