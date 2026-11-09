"""HTTP metadata permitted in research publication and future collection."""
PUBLIC_HEADERS=frozenset({
    'date','content-type','content-length','content-encoding','content-language',
    'etag','last-modified','cache-control','expires','accept-ranges','retry-after',
})
def forbidden_key(name):
    normalized=name.casefold().replace('_','-')
    return any(part in normalized for part in ('cookie','authorization','token','api-key'))
def public_headers(headers):
    return {k:v for k,v in headers.items() if k.casefold() in PUBLIC_HEADERS}
def clean_public_metadata(value):
    if isinstance(value,dict):
        return {k:public_headers(v) if k.casefold()=='headers' and isinstance(v,dict) else clean_public_metadata(v)
                for k,v in value.items() if not forbidden_key(k)}
    if isinstance(value,list):return [clean_public_metadata(v) for v in value]
    return value
