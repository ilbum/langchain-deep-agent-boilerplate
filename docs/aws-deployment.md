# Production Checklist for LangChain/LangGraph Agents on AWS

## 1. Bedrock Integration

* Use Amazon Bedrock Runtime / Converse API as the preferred integration path where possible; use streaming variants for token streaming.
* Standardize model invocation behind a small adapter layer so you can swap Bedrock models, regions, throttling policies, and fallbacks.
* Validate model-specific limits: context window, tool-calling support, JSON/schema support, multimodal support, streaming support, and regional availability.
* Pin model IDs or inference profiles explicitly; avoid “latest” style behavior in production.
* Add retry/backoff for Bedrock throttling, transient 5xx errors, and network timeouts.
* Keep provider-specific prompt/tool formatting isolated from LangGraph business logic.

### AWS-Specific

* Request/enable Bedrock model access per account and region before deployment.
* Prefer Converse / ConverseStream for a unified Bedrock API across models.
* Use cross-region inference profiles where supported for availability and quota flexibility.
* For predictable latency/capacity, consider Provisioned Throughput for supported models.

## 2. Model Credentials and Access Control

* Do not store AWS keys in app config or LangChain settings.
* Use IAM roles for ECS, EKS, Lambda, EC2, SageMaker, or Bedrock-hosted workloads.
* Scope IAM permissions tightly:
  + `bedrock:InvokeModel`
  + `bedrock:InvokeModelWithResponseStream`
  + `bedrock:Converse`
  + `bedrock:ConverseStream`
  + guardrail permissions if used
* Separate roles for dev, staging, prod, CI, evaluation jobs, and human operators.
* Use account/region allowlists for model access.

### AWS-Specific

* Use STS AssumeRole for CI/CD and cross-account deployments.
* Store non-AWS secrets in AWS Secrets Manager or SSM Parameter Store.
* Use VPC endpoints / AWS PrivateLink where available to reduce public internet exposure.
* Log caller identity in Bedrock invocation logs to attribute usage by role/service.

## 3. Streaming

* Decide what you stream:
  + raw model tokens
  + LangGraph node updates
  + tool-calls events
  + final responses only
* Use streaming for UX, but keep durable state writes independent from client connections.
* Handle disconnects, retries, and replay/resume semantics.
* Avoid streaming sensitive intermediate chain-of-thought or internal tool data to users.
* Backpressure outbound token streams to avoid overwhelming clients.

### AWS-Specific

* Use ConverseStream or InvokeModelWithResponseStream.
* For web apps, use API Gateway WebSockets, ALB streaming, AppSync subscriptions, or direct service streaming depending on latency and auth needs.
* Be careful with Lambda streaming/timeouts for long agent runs; ECS/Fargate or EKS may be better for long-lived streams.

## 4. Long-Running Tasks

* Do not assume an agent run will fit inside a synchronous HTTP request.
* Use LangGraph checkpoints so runs can pause, resume, retry, or wait for human approval.
* Separate “start run” from “get status / stream updates / retrieve result.”
* Make tool calls idempotent, especially for writes, payments, ticket creation, database updates, and emails.
* Add cancellation, timeout, and maximum-step controls.
* Persist intermediate state before expensive or irreversible operations.

### AWS-Specific

* Use Step Functions for orchestration, retries, human approval, and long-running workflows.
* Use SQS/EventBridge for asynchronous agent job dispatch.
* Use ECS/Fargate or EKS for long-running workers.
* Avoid relying on Lambda for workflows that may exceed its timeout or need persistent streaming connections.

## 5. State Persistence and Memory

* Use LangGraph checkpointers for durable execution state.
* Distinguish between:
  + short-term run state
  + conversation history
  + long-term user memory
  + vector/RAG memory
  + audit logs
* Version your graph state schema.
* Encrypt persisted state.
* Apply retention policies for prompts, outputs, tool results, and user data.
* Store enough state to replay/debug failures, but avoid storing unnecessary sensitive data.

### AWS-Specific

* Good persistence options:
  + DynamoDB for checkpoint/state storage with high concurrency
  + Aurora PostgreSQL for relational state and transactional workflows
  + S3 for transcripts, artifacts, traces, and large payloads
  + OpenSearch Serverless or vector DB integrations for retrieval
* Use KMS encryption for DynamoDB, S3, OpenSearch, Aurora, and logs.
* Use DynamoDB conditional writes or optimistic locking for concurrent graph updates.

## 6. Concurrency, Scaling, and Quotas

* Define max concurrent agent runs per tenant/user/service.
* Limit concurrent tool calls inside each agent.
* Use semaphores/rate limiters around Bedrock calls and expensive tools.
* Add queueing instead of letting traffic spike directly into Bedrock.
* Track and handle model-specific quotas, tokens-per-minute, requests-per-minute, and region limits.
* Design graceful degradation: smaller model, no-RAG mode, async response, cached response, or human handoff.

### AWS-Specific

* Use SQS + ECS/Fargate/EKS workers for scalable background execution.
* Use Application Auto Scaling based on queue depth, CPU, memory, or custom CloudWatch metrics.
* Request Bedrock quota increases ahead of launch.
* Consider separate AWS accounts or regions for isolation between tenants/environments.

## 7. Safety and Guardrails

* Add defense-in-depth:
  + input validation
  + prompt injection detection
  + tool allowlists
  + output filtering
  + PII redaction
  + human approval for risky actions
  + policy checks before external side effects
* Treat tools as privileged operations.
* Never let the model directly choose arbitrary API endpoints, SQL, shell commands, or IAM actions without validation.
* Sanitize retrieved documents and tool outputs before inserting into prompts.
* Log safety interventions for review.

### AWS-Specific

* Use Amazon Bedrock Guardrails for content filters, denied topics, sensitive information filtering, prompt attack protections, contextual grounding, and other safety policies.
* Apply guardrails consistently at model boundaries, not only in the UI.
* Use IAM permission boundaries so even compromised agent logic cannot exceed allowed AWS actions.
* For high-risk workflows, require human approval via Step Functions, ticketing, or an internal review console.

## 8. Cost Controls

* Track cost per run, tenant, user, model, graph node, and tool.
* Enforce token budgets:
  + max input tokens
  + max output tokens
  + max graph steps
  + max tool calls
  + max retries
* Truncate, summarize, or window conversation history.
* Cache stable retrieval results and deterministic tool outputs.
* Use cheaper models for routing, classification, extraction, and summarization where acceptable.
* Run batch evaluations and load tests before production launch.

### AWS-Specific

* Use AWS Budgets, Cost Explorer, and cost allocation tags.
* Enable Bedrock invocation logging to capture metadata and token counts.
* Create CloudWatch alarms for abnormal invocation volume, latency, error rates, and token usage.
* Use separate accounts/projects for experimentation to avoid runaway spend.
* Consider Provisioned Throughput only when utilization justifies it.

## 9. Evaluations and Testing

* Build an evaluation set before launch:
  + happy paths
  + adversarial prompts
  + tool misuse attempts
  + hallucination cases
  + RAG grounding cases
  + privacy/PII cases
  + long conversation cases
  + concurrency cases
* Evaluate at multiple levels:
  + prompt/model output
  + graph path correctness
  + tool-call correctness
  + final answer quality
  + safety compliance
  + latency and cost
* Add regression tests for graph changes.
* Use deterministic fixtures for tools and retrieval during CI.
* Track eval results over time by model version, prompt version, graph version, and dataset version.

### AWS-Specific

* Store eval datasets in S3 with versioning.
* Run scheduled evals using CodeBuild, Step Functions, ECS tasks, or SageMaker Processing.
* Use CloudWatch dashboards or a warehouse/Athena pipeline for eval trend reporting.
* Include Bedrock model/region IDs in eval metadata.

## 10. Tracing and Observability

* Capture:
  + run ID
  + user/tenant ID
  + graph version
  + model ID
  + prompt version
  + node timings
  + tool calls
  + retries
  + token counts
  + guardrail actions
  + errors
  + final status
* Correlate application logs, Bedrock invocations, tool logs, and user-facing requests with a shared trace/run ID.
* Redact or hash sensitive prompt data where possible.
* Set SLOs for latency, success rate, safety intervention rate, cost per run, and tool failure rate.

### AWS-Specific

* Enable Amazon Bedrock model invocation logging; it is disabled by default.
* Bedrock invocation logs can include metadata, token counts, caller ARN, and runtime calls such as Converse, ConverseStream, InvokeModel, and streaming invocations.
* Send logs to CloudWatch Logs and/or S3; use S3 for large payloads.
* Use CloudWatch Metrics, Logs Insights, X-Ray/OpenTelemetry, and alarms.
* Use CloudTrail for control-plane auditing.
* Consider LangSmith for LangChain/LangGraph traces, evaluations, prompt/version tracking, and debugging; correlate LangSmith run IDs with AWS trace IDs.

## 11. CI/CD and Release Management

* Treat agents as software, not just prompts.
* Version:
  + graph code
  + prompts
  + model IDs
  + tool schemas
  + retrieval indexes
  + guardrail configs
  + eval datasets
* Run unit tests, graph tests, prompt/eval tests, security scans, and load tests before production.
* Use staged deployments: dev → staging → canary → production.
* Support fast rollback of prompts, graph versions, model versions, and guardrail configs.
* Use infrastructure as code for AWS resources.

### AWS-Specific

* Use CDK, Terraform, or CloudFormation for Bedrock-adjacent infrastructure, IAM, queues, databases, dashboards, alarms, and networking.
* Use CodePipeline/CodeBuild/GitHub Actions with OIDC/AssumeRole instead of static AWS keys.
* Deploy containers to ECS/Fargate or EKS for long-running agents.
* Use blue/green or canary deployments via ECS, EKS, Lambda aliases, or weighted routing.
* Keep separate AWS accounts for dev/staging/prod using AWS Organizations.

## Short AWS Production Best-Practice Summary

* Prefer IAM roles over static credentials.
* Use Converse / ConverseStream for Bedrock model calls where supported.
* Enable Bedrock invocation logging early, but apply privacy controls.
* Use Bedrock Guardrails plus application-level policy checks.
* Use DynamoDB/Aurora/S3 for durable LangGraph state, not in-memory state.
* Use SQS/EventBridge/Step Functions for async and long-running agent workflows.
* Use ECS/Fargate or EKS for workers that exceed Lambda’s practical execution model.
* Set quotas, budgets, token limits, max steps, and per-tenant rate limits.
* Add LangSmith/OpenTelemetry/CloudWatch tracing before launch, not after incidents.
* Make every tool call validated, authorized, idempotent, observable, and reversible where possible.
