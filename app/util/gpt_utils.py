from typing import Any


def enforce_additional_properties_false(schema: Any) -> Any:
    """
    OpenAI Structured Outputs(json_schema, strict=True) 제약:
    object 스키마는 additionalProperties=false 가 필요하다.
    Pydantic이 생성한 JSON Schema에 이를 재귀적으로 주입한다.
    """
    if isinstance(schema, list):
        return [enforce_additional_properties_false(s) for s in schema]

    if not isinstance(schema, dict):
        return schema

    # object 타입이면 additionalProperties를 명시적으로 false로 고정
    if schema.get("type") == "object" and "additionalProperties" not in schema:
        schema["additionalProperties"] = False

    # 자주 등장하는 하위 스키마 컨테이너들 재귀 순회
    dict_children_keys = ("properties", "$defs", "definitions")
    for key in dict_children_keys:
        child = schema.get(key)
        if isinstance(child, dict):
            for k, v in child.items():
                child[k] = enforce_additional_properties_false(v)

    list_children_keys = ("anyOf", "oneOf", "allOf", "prefixItems")
    for key in list_children_keys:
        child = schema.get(key)
        if isinstance(child, list):
            schema[key] = [enforce_additional_properties_false(v) for v in child]

    # 단일 하위 스키마들
    for key in ("items", "not", "if", "then", "else"):
        child = schema.get(key)
        if isinstance(child, (dict, list)):
            schema[key] = enforce_additional_properties_false(child)

    # additionalProperties가 dict로 오는 케이스도 대비(여기선 false로 고정하는 게 목적이지만, 안전하게 재귀 처리)
    ap = schema.get("additionalProperties")
    if isinstance(ap, dict):
        schema["additionalProperties"] = enforce_additional_properties_false(ap)

    return schema
