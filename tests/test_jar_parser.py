# tests/test_jar_parser.py
from parsers.jar_parser import (
    _is_key_class,
    _classify_file,
    _extract_annotations,
    _extract_methods,
    prepare_code_for_ai,
)


def test_is_key_class():
    assert _is_key_class("UserController.java")
    assert _is_key_class("OrderService.java")
    assert _is_key_class("PayServiceImpl.java")
    assert not _is_key_class("UserDTO.java")
    assert not _is_key_class("Constants.java")


def test_classify_file():
    assert _classify_file("UserController.java") == "controller"
    assert _classify_file("UserResource.java") == "controller"
    assert _classify_file("UserService.java") == "service"
    assert _classify_file("UserServiceImpl.java") == "service"


def test_extract_annotations():
    code = '''
    @RestController
    @RequestMapping("/api/users")
    public class UserController {
        @PostMapping
        public User create(@Valid @RequestBody UserDTO dto) {}
    }
    '''
    annotations = _extract_annotations(code)
    assert "RestController" in annotations
    assert "RequestMapping" in annotations
    assert "Valid" in annotations
    assert "RequestBody" in annotations


def test_extract_methods():
    code = '''
    public String getName(String id) {
        if (id == null) {
            throw new IllegalArgumentException("id is null");
        }
        return "name";
    }
    '''
    methods = _extract_methods(code)
    assert len(methods) == 1
    assert methods[0]["name"] == "getName"
    assert methods[0]["has_branches"] is True
    assert methods[0]["has_exception_handling"] is True


def test_prepare_code_for_ai():
    classes = [
        {"file": "A.java", "content": "class A {}", "methods": []},
        {"file": "B.java", "content": "class B {}", "methods": []},
    ]
    chunks = prepare_code_for_ai(classes, max_chars=100)
    assert len(chunks) >= 1
    assert "A.java" in chunks[0]
