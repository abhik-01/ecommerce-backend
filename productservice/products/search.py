import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_es_client():
    from elasticsearch import Elasticsearch
    return Elasticsearch(settings.ELASTICSEARCH_HOST)


def index_product(product) -> None:
    try:
        client = _get_es_client()
        doc = {
            'id': product.id,
            'title': product.title,
            'description': product.description,
            'price': float(product.price),
            'category': product.category.name if product.category else '',
            'image_url': product.image_url,
        }
        client.index(index='products', id=product.id, body=doc)
    except Exception as exc:
        logger.warning("ES index failed for product %s: %s", product.id, exc)


def delete_product_from_index(product_id: int) -> None:
    try:
        client = _get_es_client()
        client.delete(index='products', id=product_id, ignore=[404])
    except Exception as exc:
        logger.warning("ES delete failed for product %s: %s", product_id, exc)


def search_products(query: str = '', category: str = '', min_price: float = None, max_price: float = None) -> list:
    try:
        client = _get_es_client()
        must_clauses = []
        filter_clauses = []

        if query:
            must_clauses.append({
                'multi_match': {
                    'query': query,
                    'fields': ['title^2', 'description'],
                    'fuzziness': 'AUTO',
                }
            })

        if category:
            filter_clauses.append({'term': {'category.keyword': category}})

        if min_price is not None or max_price is not None:
            range_filter: dict = {}
            if min_price is not None:
                range_filter['gte'] = min_price
            if max_price is not None:
                range_filter['lte'] = max_price
            filter_clauses.append({'range': {'price': range_filter}})

        es_query: dict = {'bool': {}}
        if must_clauses:
            es_query['bool']['must'] = must_clauses
        if filter_clauses:
            es_query['bool']['filter'] = filter_clauses
        if not must_clauses and not filter_clauses:
            es_query = {'match_all': {}}

        response = client.search(index='products', body={'query': es_query, 'size': 50})
        return [hit['_source'] for hit in response['hits']['hits']]
    except Exception as exc:
        logger.warning("ES search failed: %s", exc)
        return []


def create_products_index() -> None:
    try:
        client = _get_es_client()
        if client.indices.exists(index='products'):
            return
        mappings = {
            'mappings': {
                'properties': {
                    'id': {'type': 'integer'},
                    'title': {'type': 'text', 'analyzer': 'standard'},
                    'description': {'type': 'text', 'analyzer': 'standard'},
                    'price': {'type': 'float'},
                    'category': {'type': 'text', 'fields': {'keyword': {'type': 'keyword'}}},
                    'image_url': {'type': 'keyword'},
                }
            }
        }
        client.indices.create(index='products', body=mappings)
        logger.info("Created 'products' Elasticsearch index")
    except Exception as exc:
        logger.warning("ES index creation failed: %s", exc)
