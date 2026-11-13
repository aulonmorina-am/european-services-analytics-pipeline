-- Layer schemas are set per folder in dbt_project.yml (+schema: staging|intermediate|marts).
-- With --target dev every layer schema is prefixed with dev_ (dev_staging, dev_marts, ...),
-- so local runs never touch the prod schemas in ANALYTICS. With --target prod the layer
-- schemas are used as-is.
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name == 'dev' -%}
        dev_{{ custom_schema_name | trim }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
