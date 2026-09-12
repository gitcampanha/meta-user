import unittest
from unittest.mock import Mock
from relatorio_meta import Meta, MetaError, ratio, collect

class Checks(unittest.TestCase):
    def response(self, payload, status=200):
        return Mock(status_code=status,json=Mock(return_value=payload))
    def test_all_pages_and_no_next_url_followed(self):
        api=Meta('SECRET','act_123')
        api.session.get=Mock(side_effect=[self.response({'data':[{'id':1}],'paging':{'next':'https://untrusted.invalid/?access_token=SECRET','cursors':{'after':'second'}}}),self.response({'data':[{'id':2}]})])
        self.assertEqual(len(api.get('/insights')),2)
        self.assertEqual(api.session.get.call_args.args[0],api.base+'/insights')
        self.assertEqual(api.session.get.call_args.kwargs['params']['after'],'second')
    def test_failure_is_not_empty_and_redacts_secrets(self):
        api=Meta('SECRET','123')
        api.session.get=Mock(return_value=self.response({'error':{'code':190,'message':'SECRET'}},400))
        with self.assertRaises(MetaError) as exc: api.get('/insights')
        self.assertNotIn('SECRET',str(exc.exception))
    def test_broken_pagination_fails(self):
        api=Meta('SECRET','123')
        api.session.get=Mock(return_value=self.response({'data':[],'paging':{'next':'anything'}}))
        with self.assertRaises(MetaError): api.get('/insights')
    def test_zero_denominator_is_unavailable(self):
        self.assertIsNone(ratio(100,0))
        self.assertIsNone(ratio(None,10))
        self.assertEqual(ratio(0,10),0)
    def test_optional_failure_marked(self):
        api=Mock()
        def get(*args,**kwargs):
            if kwargs.get('breakdowns'): raise MetaError('Indisponivel')
            return []
        api.get.side_effect=get
        result=collect(api,'2026-09-01','2026-09-02')
        self.assertIsNone(result['regions'])
        self.assertEqual(len(result['warnings']),2)
    def test_core_failure_stops(self):
        api=Mock(); api.get.side_effect=MetaError('Falha')
        with self.assertRaises(MetaError): collect(api,'2026-09-01','2026-09-02')

if __name__ == '__main__': unittest.main()
