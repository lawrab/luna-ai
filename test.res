============================= test session starts ==============================
platform linux -- Python 3.11.13, pytest-8.4.1, pluggy-1.6.0
rootdir: /home/lrabbets/repos/luna-ai
configfile: pytest.ini
testpaths: tests
plugins: mock-3.14.1, langsmith-0.4.13, anyio-4.10.0, asyncio-1.1.0
asyncio: mode=Mode.STRICT, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 4 items

tests/test_agent.py FF                                                   [ 50%]
tests/test_tools.py ..                                                   [100%]

=================================== FAILURES ===================================
_________________________ test_agent_handles_tool_call _________________________

self = <unittest.mock._patch object at 0x7ffff440fcd0>

    def __enter__(self):
        """Perform the patch."""
        new, spec, spec_set = self.new, self.spec, self.spec_set
        autospec, kwargs = self.autospec, self.kwargs
        new_callable = self.new_callable
        self.target = self.getter()
    
        # normalise False to None
        if spec is False:
            spec = None
        if spec_set is False:
            spec_set = None
        if autospec is False:
            autospec = None
    
        if spec is not None and autospec is not None:
            raise TypeError("Can't specify spec and autospec")
        if ((spec is not None or autospec is not None) and
            spec_set not in (True, None)):
            raise TypeError("Can't provide explicit spec_set *and* spec or autospec")
    
        original, local = self.get_original()
    
        if new is DEFAULT and autospec is None:
            inherit = False
            if spec is True:
                # set spec to the object we are replacing
                spec = original
                if spec_set is True:
                    spec_set = original
                    spec = None
            elif spec is not None:
                if spec_set is True:
                    spec_set = spec
                    spec = None
            elif spec_set is True:
                spec_set = original
    
            if spec is not None or spec_set is not None:
                if original is DEFAULT:
                    raise TypeError("Can't use 'spec' with create=True")
                if isinstance(original, type):
                    # If we're patching out a class and there is a spec
                    inherit = True
            if spec is None and _is_async_obj(original):
                Klass = AsyncMock
            else:
                Klass = MagicMock
            _kwargs = {}
            if new_callable is not None:
                Klass = new_callable
            elif spec is not None or spec_set is not None:
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if _is_list(this_spec):
                    not_callable = '__call__' not in this_spec
                else:
                    not_callable = not callable(this_spec)
                if _is_async_obj(this_spec):
                    Klass = AsyncMock
                elif not_callable:
                    Klass = NonCallableMagicMock
    
            if spec is not None:
                _kwargs['spec'] = spec
            if spec_set is not None:
                _kwargs['spec_set'] = spec_set
    
            # add a name to mocks
            if (isinstance(Klass, type) and
                issubclass(Klass, NonCallableMock) and self.attribute):
                _kwargs['name'] = self.attribute
    
            _kwargs.update(kwargs)
            new = Klass(**_kwargs)
    
            if inherit and _is_instance_mock(new):
                # we can only tell if the instance should be callable if the
                # spec is not a list
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if (not _is_list(this_spec) and not
                    _instance_callable(this_spec)):
                    Klass = NonCallableMagicMock
    
                _kwargs.pop('name')
                new.return_value = Klass(_new_parent=new, _new_name='()',
                                         **_kwargs)
        elif autospec is not None:
            # spec is ignored, new *must* be default, spec_set is treated
            # as a boolean. Should we check spec is not None and that spec_set
            # is a bool?
            if new is not DEFAULT:
                raise TypeError(
                    "autospec creates the mock for you. Can't specify "
                    "autospec and new."
                )
            if original is DEFAULT:
                raise TypeError("Can't use 'autospec' with create=True")
            spec_set = bool(spec_set)
            if autospec is True:
                autospec = original
    
            if _is_instance_mock(self.target):
                raise InvalidSpecError(
                    f'Cannot autospec attr {self.attribute!r} as the patch '
                    f'target has already been mocked out. '
                    f'[target={self.target!r}, attr={autospec!r}]')
            if _is_instance_mock(autospec):
                target_name = getattr(self.target, '__name__', self.target)
                raise InvalidSpecError(
                    f'Cannot autospec attr {self.attribute!r} from target '
                    f'{target_name!r} as it has already been mocked out. '
                    f'[target={self.target!r}, attr={autospec!r}]')
    
            new = create_autospec(autospec, spec_set=spec_set,
                                  _name=self.attribute, **kwargs)
        elif kwargs:
            # can't set keyword args when we aren't creating the mock
            # XXXX If new is a Mock we could call new.configure_mock(**kwargs)
            raise TypeError("Can't pass kwargs to a mock we aren't creating")
    
        new_attr = new
    
        self.temp_original = original
        self.is_local = local
        self._exit_stack = contextlib.ExitStack()
        try:
>           setattr(self.target, self.attribute, new_attr)

/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1555: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.11/site-packages/pydantic/main.py:997: in __setattr__
    elif (setattr_handler := self._setattr_handler(name, value)) is not None:
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = ChatPromptTemplate(input_variables=['input'], input_types={}, partial_variables={}, messages=[SystemMessagePromptTempl..._types={}, partial_variables={}, template='{input}'), additional_kwargs={})])
| RunnableLambda(...)
| StrOutputParser()
name = 'ainvoke', value = <AsyncMock name='ainvoke' id='140737291288208'>

    def _setattr_handler(self, name: str, value: Any) -> Callable[[BaseModel, str, Any], None] | None:
        """Get a handler for setting an attribute on the model instance.
    
        Returns:
            A handler for setting an attribute on the model instance. Used for memoization of the handler.
            Memoizing the handlers leads to a dramatic performance improvement in `__setattr__`
            Returns `None` when memoization is not safe, then the attribute is set directly.
        """
        cls = self.__class__
        if name in cls.__class_vars__:
            raise AttributeError(
                f'{name!r} is a ClassVar of `{cls.__name__}` and cannot be set on an instance. '
                f'If you want to set a value on the class, use `{cls.__name__}.{name} = value`.'
            )
        elif not _fields.is_valid_field_name(name):
            if (attribute := cls.__private_attributes__.get(name)) is not None:
                if hasattr(attribute, '__set__'):
                    return lambda model, _name, val: attribute.__set__(model, val)
                else:
                    return _SIMPLE_SETATTR_HANDLERS['private']
            else:
                _object_setattr(self, name, value)
                return None  # Can not return memoized handler with possibly freeform attr names
    
        attr = getattr(cls, name, None)
        # NOTE: We currently special case properties and `cached_property`, but we might need
        # to generalize this to all data/non-data descriptors at some point. For non-data descriptors
        # (such as `cached_property`), it isn't obvious though. `cached_property` caches the value
        # to the instance's `__dict__`, but other non-data descriptors might do things differently.
        if isinstance(attr, cached_property):
            return _SIMPLE_SETATTR_HANDLERS['cached_property']
    
        _check_frozen(cls, name, value)
    
        # We allow properties to be set only on non frozen models for now (to match dataclasses).
        # This can be changed if it ever gets requested.
        if isinstance(attr, property):
            return lambda model, _name, val: attr.__set__(model, val)
        elif cls.model_config.get('validate_assignment'):
            return _SIMPLE_SETATTR_HANDLERS['validate_assignment']
        elif name not in cls.__pydantic_fields__:
            if cls.model_config.get('extra') != 'allow':
                # TODO - matching error
>               raise ValueError(f'"{cls.__name__}" object has no field "{name}"')
E               ValueError: "RunnableSequence" object has no field "ainvoke"

.venv/lib/python3.11/site-packages/pydantic/main.py:1044: ValueError

During handling of the above exception, another exception occurred:

self = ChatPromptTemplate(input_variables=['input'], input_types={}, partial_variables={}, messages=[SystemMessagePromptTempl..._types={}, partial_variables={}, template='{input}'), additional_kwargs={})])
| RunnableLambda(...)
| StrOutputParser()
item = 'ainvoke'

    def __delattr__(self, item: str) -> Any:
        cls = self.__class__
    
        if item in self.__private_attributes__:
            attribute = self.__private_attributes__[item]
            if hasattr(attribute, '__delete__'):
                attribute.__delete__(self)  # type: ignore
                return
    
            try:
                # Note: self.__pydantic_private__ cannot be None if self.__private_attributes__ has items
                del self.__pydantic_private__[item]  # type: ignore
                return
            except KeyError as exc:
                raise AttributeError(f'{cls.__name__!r} object has no attribute {item!r}') from exc
    
        # Allow cached properties to be deleted (even if the class is frozen):
        attr = getattr(cls, item, None)
        if isinstance(attr, cached_property):
            return object.__delattr__(self, item)
    
        _check_frozen(cls, name=item, value=None)
    
        if item in self.__pydantic_fields__:
            object.__delattr__(self, item)
        elif self.__pydantic_extra__ is not None and item in self.__pydantic_extra__:
            del self.__pydantic_extra__[item]
        else:
            try:
>               object.__delattr__(self, item)
E               AttributeError: 'RunnableSequence' object has no attribute 'ainvoke'

.venv/lib/python3.11/site-packages/pydantic/main.py:1084: AttributeError

During handling of the above exception, another exception occurred:

mocker = <pytest_mock.plugin.MockerFixture object at 0x7ffff43fcd10>

    @pytest.mark.asyncio
    async def test_agent_handles_tool_call(mocker):
        """
        Tests that the agent, when given a tool-calling response from the LLM,
        correctly calls the underlying system command asynchronously.
        """
        # Mock asyncio.create_subprocess_exec for the tool execution
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'', b'') # Mock stdout, stderr
        mock_create_subprocess_exec = mocker.patch(
            'luna.tools.asyncio.create_subprocess_exec',
            return_value=mock_process
        )
    
        # Mock events.publish
        mock_publish = mocker.patch('luna.events.publish')
    
        # Mock the agent's chain.ainvoke directly
        tool_call_json = json.dumps({
            "tool_name": "send_desktop_notification",
            "tool_args": {
                "title": "Test from Agent",
                "message": "This is a test."
            }
        })
        # Create the agent instance
        agent = LunaAgent(llm=MagicMock()) # LLM doesn't matter if its a mock, its ainvoke is patched
    
        # Mock agent.chain.ainvoke directly
>       mocker.patch.object(agent.chain, 'ainvoke', new_callable=AsyncMock, return_value=tool_call_json)

tests/test_agent.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.11/site-packages/pytest_mock/plugin.py:288: in object
    return self._start_patch(
.venv/lib/python3.11/site-packages/pytest_mock/plugin.py:257: in _start_patch
    mocked: MockType = p.start()
                       ^^^^^^^^^
/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1594: in start
    result = self.__enter__()
             ^^^^^^^^^^^^^^^^
/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1568: in __enter__
    if not self.__exit__(*sys.exc_info()):
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1576: in __exit__
    delattr(self.target, self.attribute)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = ChatPromptTemplate(input_variables=['input'], input_types={}, partial_variables={}, messages=[SystemMessagePromptTempl..._types={}, partial_variables={}, template='{input}'), additional_kwargs={})])
| RunnableLambda(...)
| StrOutputParser()
item = 'ainvoke'

    def __delattr__(self, item: str) -> Any:
        cls = self.__class__
    
        if item in self.__private_attributes__:
            attribute = self.__private_attributes__[item]
            if hasattr(attribute, '__delete__'):
                attribute.__delete__(self)  # type: ignore
                return
    
            try:
                # Note: self.__pydantic_private__ cannot be None if self.__private_attributes__ has items
                del self.__pydantic_private__[item]  # type: ignore
                return
            except KeyError as exc:
                raise AttributeError(f'{cls.__name__!r} object has no attribute {item!r}') from exc
    
        # Allow cached properties to be deleted (even if the class is frozen):
        attr = getattr(cls, item, None)
        if isinstance(attr, cached_property):
            return object.__delattr__(self, item)
    
        _check_frozen(cls, name=item, value=None)
    
        if item in self.__pydantic_fields__:
            object.__delattr__(self, item)
        elif self.__pydantic_extra__ is not None and item in self.__pydantic_extra__:
            del self.__pydantic_extra__[item]
        else:
            try:
                object.__delattr__(self, item)
            except AttributeError:
>               raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}')
E               AttributeError: 'RunnableSequence' object has no attribute 'ainvoke'

.venv/lib/python3.11/site-packages/pydantic/main.py:1086: AttributeError
____________________ test_agent_handles_normal_conversation ____________________

self = <unittest.mock._patch object at 0x7ffff4241850>

    def __enter__(self):
        """Perform the patch."""
        new, spec, spec_set = self.new, self.spec, self.spec_set
        autospec, kwargs = self.autospec, self.kwargs
        new_callable = self.new_callable
        self.target = self.getter()
    
        # normalise False to None
        if spec is False:
            spec = None
        if spec_set is False:
            spec_set = None
        if autospec is False:
            autospec = None
    
        if spec is not None and autospec is not None:
            raise TypeError("Can't specify spec and autospec")
        if ((spec is not None or autospec is not None) and
            spec_set not in (True, None)):
            raise TypeError("Can't provide explicit spec_set *and* spec or autospec")
    
        original, local = self.get_original()
    
        if new is DEFAULT and autospec is None:
            inherit = False
            if spec is True:
                # set spec to the object we are replacing
                spec = original
                if spec_set is True:
                    spec_set = original
                    spec = None
            elif spec is not None:
                if spec_set is True:
                    spec_set = spec
                    spec = None
            elif spec_set is True:
                spec_set = original
    
            if spec is not None or spec_set is not None:
                if original is DEFAULT:
                    raise TypeError("Can't use 'spec' with create=True")
                if isinstance(original, type):
                    # If we're patching out a class and there is a spec
                    inherit = True
            if spec is None and _is_async_obj(original):
                Klass = AsyncMock
            else:
                Klass = MagicMock
            _kwargs = {}
            if new_callable is not None:
                Klass = new_callable
            elif spec is not None or spec_set is not None:
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if _is_list(this_spec):
                    not_callable = '__call__' not in this_spec
                else:
                    not_callable = not callable(this_spec)
                if _is_async_obj(this_spec):
                    Klass = AsyncMock
                elif not_callable:
                    Klass = NonCallableMagicMock
    
            if spec is not None:
                _kwargs['spec'] = spec
            if spec_set is not None:
                _kwargs['spec_set'] = spec_set
    
            # add a name to mocks
            if (isinstance(Klass, type) and
                issubclass(Klass, NonCallableMock) and self.attribute):
                _kwargs['name'] = self.attribute
    
            _kwargs.update(kwargs)
            new = Klass(**_kwargs)
    
            if inherit and _is_instance_mock(new):
                # we can only tell if the instance should be callable if the
                # spec is not a list
                this_spec = spec
                if spec_set is not None:
                    this_spec = spec_set
                if (not _is_list(this_spec) and not
                    _instance_callable(this_spec)):
                    Klass = NonCallableMagicMock
    
                _kwargs.pop('name')
                new.return_value = Klass(_new_parent=new, _new_name='()',
                                         **_kwargs)
        elif autospec is not None:
            # spec is ignored, new *must* be default, spec_set is treated
            # as a boolean. Should we check spec is not None and that spec_set
            # is a bool?
            if new is not DEFAULT:
                raise TypeError(
                    "autospec creates the mock for you. Can't specify "
                    "autospec and new."
                )
            if original is DEFAULT:
                raise TypeError("Can't use 'autospec' with create=True")
            spec_set = bool(spec_set)
            if autospec is True:
                autospec = original
    
            if _is_instance_mock(self.target):
                raise InvalidSpecError(
                    f'Cannot autospec attr {self.attribute!r} as the patch '
                    f'target has already been mocked out. '
                    f'[target={self.target!r}, attr={autospec!r}]')
            if _is_instance_mock(autospec):
                target_name = getattr(self.target, '__name__', self.target)
                raise InvalidSpecError(
                    f'Cannot autospec attr {self.attribute!r} from target '
                    f'{target_name!r} as it has already been mocked out. '
                    f'[target={self.target!r}, attr={autospec!r}]')
    
            new = create_autospec(autospec, spec_set=spec_set,
                                  _name=self.attribute, **kwargs)
        elif kwargs:
            # can't set keyword args when we aren't creating the mock
            # XXXX If new is a Mock we could call new.configure_mock(**kwargs)
            raise TypeError("Can't pass kwargs to a mock we aren't creating")
    
        new_attr = new
    
        self.temp_original = original
        self.is_local = local
        self._exit_stack = contextlib.ExitStack()
        try:
>           setattr(self.target, self.attribute, new_attr)

/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1555: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.11/site-packages/pydantic/main.py:997: in __setattr__
    elif (setattr_handler := self._setattr_handler(name, value)) is not None:
                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = ChatPromptTemplate(input_variables=['input'], input_types={}, partial_variables={}, messages=[SystemMessagePromptTempl..._types={}, partial_variables={}, template='{input}'), additional_kwargs={})])
| RunnableLambda(...)
| StrOutputParser()
name = 'ainvoke', value = <AsyncMock name='ainvoke' id='140737289388816'>

    def _setattr_handler(self, name: str, value: Any) -> Callable[[BaseModel, str, Any], None] | None:
        """Get a handler for setting an attribute on the model instance.
    
        Returns:
            A handler for setting an attribute on the model instance. Used for memoization of the handler.
            Memoizing the handlers leads to a dramatic performance improvement in `__setattr__`
            Returns `None` when memoization is not safe, then the attribute is set directly.
        """
        cls = self.__class__
        if name in cls.__class_vars__:
            raise AttributeError(
                f'{name!r} is a ClassVar of `{cls.__name__}` and cannot be set on an instance. '
                f'If you want to set a value on the class, use `{cls.__name__}.{name} = value`.'
            )
        elif not _fields.is_valid_field_name(name):
            if (attribute := cls.__private_attributes__.get(name)) is not None:
                if hasattr(attribute, '__set__'):
                    return lambda model, _name, val: attribute.__set__(model, val)
                else:
                    return _SIMPLE_SETATTR_HANDLERS['private']
            else:
                _object_setattr(self, name, value)
                return None  # Can not return memoized handler with possibly freeform attr names
    
        attr = getattr(cls, name, None)
        # NOTE: We currently special case properties and `cached_property`, but we might need
        # to generalize this to all data/non-data descriptors at some point. For non-data descriptors
        # (such as `cached_property`), it isn't obvious though. `cached_property` caches the value
        # to the instance's `__dict__`, but other non-data descriptors might do things differently.
        if isinstance(attr, cached_property):
            return _SIMPLE_SETATTR_HANDLERS['cached_property']
    
        _check_frozen(cls, name, value)
    
        # We allow properties to be set only on non frozen models for now (to match dataclasses).
        # This can be changed if it ever gets requested.
        if isinstance(attr, property):
            return lambda model, _name, val: attr.__set__(model, val)
        elif cls.model_config.get('validate_assignment'):
            return _SIMPLE_SETATTR_HANDLERS['validate_assignment']
        elif name not in cls.__pydantic_fields__:
            if cls.model_config.get('extra') != 'allow':
                # TODO - matching error
>               raise ValueError(f'"{cls.__name__}" object has no field "{name}"')
E               ValueError: "RunnableSequence" object has no field "ainvoke"

.venv/lib/python3.11/site-packages/pydantic/main.py:1044: ValueError

During handling of the above exception, another exception occurred:

self = ChatPromptTemplate(input_variables=['input'], input_types={}, partial_variables={}, messages=[SystemMessagePromptTempl..._types={}, partial_variables={}, template='{input}'), additional_kwargs={})])
| RunnableLambda(...)
| StrOutputParser()
item = 'ainvoke'

    def __delattr__(self, item: str) -> Any:
        cls = self.__class__
    
        if item in self.__private_attributes__:
            attribute = self.__private_attributes__[item]
            if hasattr(attribute, '__delete__'):
                attribute.__delete__(self)  # type: ignore
                return
    
            try:
                # Note: self.__pydantic_private__ cannot be None if self.__private_attributes__ has items
                del self.__pydantic_private__[item]  # type: ignore
                return
            except KeyError as exc:
                raise AttributeError(f'{cls.__name__!r} object has no attribute {item!r}') from exc
    
        # Allow cached properties to be deleted (even if the class is frozen):
        attr = getattr(cls, item, None)
        if isinstance(attr, cached_property):
            return object.__delattr__(self, item)
    
        _check_frozen(cls, name=item, value=None)
    
        if item in self.__pydantic_fields__:
            object.__delattr__(self, item)
        elif self.__pydantic_extra__ is not None and item in self.__pydantic_extra__:
            del self.__pydantic_extra__[item]
        else:
            try:
>               object.__delattr__(self, item)
E               AttributeError: 'RunnableSequence' object has no attribute 'ainvoke'

.venv/lib/python3.11/site-packages/pydantic/main.py:1084: AttributeError

During handling of the above exception, another exception occurred:

mocker = <pytest_mock.plugin.MockerFixture object at 0x7ffff43fce50>

    @pytest.mark.asyncio
    async def test_agent_handles_normal_conversation(mocker):
        """
        Tests that the agent returns a simple text response when no tool is called asynchronously.
        """
        # Mock events.publish
        mock_publish = mocker.patch('luna.events.publish')
    
        # Mock the agent's chain.ainvoke directly
        chat_response = "Hello! How can I help you today?"
        # Create the agent instance
        agent = LunaAgent(llm=MagicMock()) # LLM doesn't matter if its a mock, its ainvoke is patched
    
        # Mock agent.chain.ainvoke directly
>       mocker.patch.object(agent.chain, 'ainvoke', new_callable=AsyncMock, return_value=AIMessage(content=chat_response))

tests/test_agent.py:87: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 
.venv/lib/python3.11/site-packages/pytest_mock/plugin.py:288: in object
    return self._start_patch(
.venv/lib/python3.11/site-packages/pytest_mock/plugin.py:257: in _start_patch
    mocked: MockType = p.start()
                       ^^^^^^^^^
/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1594: in start
    result = self.__enter__()
             ^^^^^^^^^^^^^^^^
/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1568: in __enter__
    if not self.__exit__(*sys.exc_info()):
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/nix/store/xldyfac0kbcl5c1yp9ygsag5y23irwxs-python3-3.11.13/lib/python3.11/unittest/mock.py:1576: in __exit__
    delattr(self.target, self.attribute)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = ChatPromptTemplate(input_variables=['input'], input_types={}, partial_variables={}, messages=[SystemMessagePromptTempl..._types={}, partial_variables={}, template='{input}'), additional_kwargs={})])
| RunnableLambda(...)
| StrOutputParser()
item = 'ainvoke'

    def __delattr__(self, item: str) -> Any:
        cls = self.__class__
    
        if item in self.__private_attributes__:
            attribute = self.__private_attributes__[item]
            if hasattr(attribute, '__delete__'):
                attribute.__delete__(self)  # type: ignore
                return
    
            try:
                # Note: self.__pydantic_private__ cannot be None if self.__private_attributes__ has items
                del self.__pydantic_private__[item]  # type: ignore
                return
            except KeyError as exc:
                raise AttributeError(f'{cls.__name__!r} object has no attribute {item!r}') from exc
    
        # Allow cached properties to be deleted (even if the class is frozen):
        attr = getattr(cls, item, None)
        if isinstance(attr, cached_property):
            return object.__delattr__(self, item)
    
        _check_frozen(cls, name=item, value=None)
    
        if item in self.__pydantic_fields__:
            object.__delattr__(self, item)
        elif self.__pydantic_extra__ is not None and item in self.__pydantic_extra__:
            del self.__pydantic_extra__[item]
        else:
            try:
                object.__delattr__(self, item)
            except AttributeError:
>               raise AttributeError(f'{type(self).__name__!r} object has no attribute {item!r}')
E               AttributeError: 'RunnableSequence' object has no attribute 'ainvoke'

.venv/lib/python3.11/site-packages/pydantic/main.py:1086: AttributeError
=========================== short test summary info ============================
FAILED tests/test_agent.py::test_agent_handles_tool_call - AttributeError: 'R...
FAILED tests/test_agent.py::test_agent_handles_normal_conversation - Attribut...
========================= 2 failed, 2 passed in 0.34s ==========================
