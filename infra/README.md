# Infrastructure Configuration

This directory contains all infrastructure-as-code assets for the development and deployment environments.

## Observability Stack

```
infra/
├── otel-collector-config.yaml   # OpenTelemetry Collector pipelines and exporters
├── prometheus.yml                # Prometheus scrape configuration
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── datasources.yaml  # Tempo and Prometheus datasource provisioning
        └── dashboards/
            ├── dashboard.yaml    # Dashboard provider configuration
            └── eip.json          # Project Observability dashboard definition
```
