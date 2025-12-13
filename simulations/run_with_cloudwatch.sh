#!/bin/bash
# Run simulator with CloudWatch telemetry export
# Traces will appear in AWS Console: CloudWatch > GenAI Observability

SERVICE_NAME="kuso-entertainment"
LOG_GROUP="/aws/bedrock-agentcore/runtimes/kuso-entertainment"

export AGENT_OBSERVABILITY_ENABLED=true
export OTEL_PYTHON_DISTRO=aws_distro
export OTEL_PYTHON_CONFIGURATOR=aws_configurator
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_METRICS_EXPORTER=awsemf
export OTEL_TRACES_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_RESOURCE_ATTRIBUTES="service.name=${SERVICE_NAME},aws.log.group.names=${LOG_GROUP}"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="x-aws-log-group=${LOG_GROUP},x-aws-log-stream=simulator,x-aws-metric-namespace=${SERVICE_NAME}"

# Evaluation Results - registers custom evaluators to AgentCore Evaluation dashboard
export EVALUATION_RESULTS_LOG_GROUP="kuso-entertainment-evals"

cd "$(dirname "$0")/.."
uv run opentelemetry-instrument python simulations/simulator.py
