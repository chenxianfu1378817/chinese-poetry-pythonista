import sys,json,types,unittest
from unittest.mock import patch,Mock
from urllib.error import HTTPError
from poetry_app import ai
class AITests(unittest.TestCase):
    def test_endpoint_and_key_binding(self):
        self.assertEqual(ai.endpoint_url('https://example.com/v1/'),'https://example.com/v1/chat/completions')
        for url in ['http://example.com','https://user:secret@example.com/v1','https://example.com/v1?key=secret']:
            with self.assertRaises(ValueError):ai.endpoint_url(url)
        self.assertNotEqual(ai.account('https://a.example/v1'),ai.account('https://b.example/v1'))
    def test_request_and_no_notes_or_key_in_body(self):
        keychain=types.SimpleNamespace(get_password=lambda *args:'TEST_KEY_NOT_REAL')
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.read.return_value=json.dumps({'choices':[{'message':{'content':'测试解读'}}]}).encode()
        opener=Mock();opener.open.return_value=response
        poem={'title':'山居秋暝','author':'王維','paragraphs':['空山新雨後'],'note':'PRIVATE_NOTE'}
        with patch.dict(sys.modules,{'keychain':keychain}),patch.object(ai,'build_opener',return_value=opener):
            self.assertEqual(ai.interpret(poem,'https://example.com/v1','test-model'),'测试解读')
        request=opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'),'Bearer TEST_KEY_NOT_REAL')
        self.assertNotIn(b'TEST_KEY_NOT_REAL',request.data);self.assertNotIn(b'PRIVATE_NOTE',request.data)
    def test_missing_key_does_not_call_network(self):
        with patch.dict(sys.modules,{'keychain':types.SimpleNamespace(get_password=lambda *args:None)}),patch.object(ai,'build_opener') as network:
            with self.assertRaises(ValueError):ai.interpret({},'https://example.com/v1','model')
            network.assert_not_called()
    def test_provider_error_is_sanitized(self):
        keychain=types.SimpleNamespace(get_password=lambda *args:'TEST_KEY_NOT_REAL')
        opener=Mock();opener.open.side_effect=HTTPError('https://example.com',401,'TEST_KEY_NOT_REAL',None,None)
        poem={'title':'x','author':'x','paragraphs':['x']}
        with patch.dict(sys.modules,{'keychain':keychain}),patch.object(ai,'build_opener',return_value=opener):
            with self.assertRaises(RuntimeError) as error:ai.interpret(poem,'https://example.com/v1','model')
            self.assertNotIn('TEST_KEY_NOT_REAL',str(error.exception));self.assertIn('401',str(error.exception))
if __name__=='__main__':unittest.main()
