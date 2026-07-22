from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DecisionState, Policy, PolicyStatus, Tenant, TenantStatus


class TenantNotFoundError(LookupError):
    pass


class PolicyNotFoundError(LookupError):
    pass


class PolicyStateError(RuntimeError):
    pass


@dataclass(slots=True)
class PolicyDecision:
    state: DecisionState
    reason: str
    matched_rule_id: str | None
    trace: list[dict[str, Any]]
    policy: Policy | None
    approval_requirement: dict[str, Any] | None = None
    evidence_requirement: dict[str, Any] | None = None


class PolicyManagementService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_tenant(self, display_name: str, finance_profile: str) -> Tenant:
        tenant = Tenant(
            tenant_id=uuid4().hex,
            display_name=display_name,
            finance_profile=finance_profile,
            status=TenantStatus.active,
        )
        self.session.add(tenant)
        self.session.commit()
        self.session.refresh(tenant)
        return tenant

    def list_tenants(self) -> list[Tenant]:
        return list(self.session.scalars(select(Tenant).order_by(Tenant.created_at.asc())))

    def get_tenant(self, tenant_id: str) -> Tenant:
        tenant = self.session.get(Tenant, tenant_id)
        if tenant is None:
            raise TenantNotFoundError(f"tenant '{tenant_id}' was not found")
        return tenant

    def create_policy(
        self,
        *,
        tenant_id: str,
        name: str,
        description: str | None,
        workflow_key: str,
        default_decision: DecisionState,
        finance_action_classes: list[str],
        rules: list[dict[str, Any]],
    ) -> Policy:
        self.get_tenant(tenant_id)
        current_version = self.session.scalar(
            select(func.max(Policy.version)).where(
                Policy.tenant_id == tenant_id,
                Policy.workflow_key == workflow_key,
            )
        )
        policy = Policy(
            policy_id=uuid4().hex,
            tenant_id=tenant_id,
            name=name,
            description=description,
            workflow_key=workflow_key,
            version=(current_version or 0) + 1,
            status=PolicyStatus.draft,
            default_decision=default_decision,
            finance_action_classes=finance_action_classes,
            rules=rules,
        )
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def list_policies(
        self,
        *,
        tenant_id: str | None = None,
        workflow_key: str | None = None,
        status: PolicyStatus | None = None,
    ) -> list[Policy]:
        query = select(Policy).order_by(Policy.created_at.asc())
        if tenant_id is not None:
            query = query.where(Policy.tenant_id == tenant_id)
        if workflow_key is not None:
            query = query.where(Policy.workflow_key == workflow_key)
        if status is not None:
            query = query.where(Policy.status == status)
        return list(self.session.scalars(query))

    def get_policy(self, policy_id: str) -> Policy:
        policy = self.session.get(Policy, policy_id)
        if policy is None:
            raise PolicyNotFoundError(f"policy '{policy_id}' was not found")
        return policy

    def update_policy(
        self,
        policy_id: str,
        *,
        name: str,
        description: str | None,
        default_decision: DecisionState,
        finance_action_classes: list[str],
        rules: list[dict[str, Any]],
    ) -> Policy:
        policy = self.get_policy(policy_id)
        if policy.status != PolicyStatus.draft:
            raise PolicyStateError("only draft policies may be updated")

        policy.name = name
        policy.description = description
        policy.default_decision = default_decision
        policy.finance_action_classes = finance_action_classes
        policy.rules = rules

        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def activate_policy(self, policy_id: str) -> Policy:
        policy = self.get_policy(policy_id)
        if policy.status == PolicyStatus.retired:
            raise PolicyStateError("retired policies may not be reactivated")

        active_policies = list(
            self.session.scalars(
                select(Policy).where(
                    Policy.tenant_id == policy.tenant_id,
                    Policy.workflow_key == policy.workflow_key,
                    Policy.status == PolicyStatus.active,
                    Policy.policy_id != policy.policy_id,
                )
            )
        )
        for active_policy in active_policies:
            active_policy.status = PolicyStatus.retired
            self.session.add(active_policy)

        policy.status = PolicyStatus.active
        policy.activated_at = policy.activated_at or datetime.now(UTC)
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        return policy

    def get_active_policy(self, tenant_id: str, workflow_key: str) -> Policy | None:
        return self.session.scalar(
            select(Policy)
            .where(
                Policy.tenant_id == tenant_id,
                Policy.workflow_key == workflow_key,
                Policy.status == PolicyStatus.active,
            )
            .order_by(Policy.version.desc())
        )


class PolicyEngine:
    def evaluate(
        self,
        *,
        action_intent: dict[str, Any],
        intake_context: dict[str, Any],
        evaluation_context: dict[str, Any],
        policy: Policy | None,
        contract_supported: bool,
        contract_valid: bool,
        contract_errors: list[str],
    ) -> PolicyDecision:
        if not contract_supported:
            return PolicyDecision(
                state=DecisionState.structurally_non_executable,
                reason="unsupported external Action Intent contract version",
                matched_rule_id=None,
                trace=[{"type": "hard_rule", "matched": True, "reason": "unsupported_contract"}],
                policy=None,
                approval_requirement=None,
                evidence_requirement=None,
            )

        if not contract_valid:
            return PolicyDecision(
                state=DecisionState.structurally_non_executable,
                reason="external Action Intent failed versioned contract validation",
                matched_rule_id=None,
                trace=[
                    {
                        "type": "hard_rule",
                        "matched": True,
                        "reason": "contract_validation_failed",
                        "errors": contract_errors,
                    }
                ],
                policy=None,
                approval_requirement=None,
                evidence_requirement=None,
            )

        if intake_context.get("workflow_mismatch") or intake_context.get("routing_mismatch"):
            return PolicyDecision(
                state=DecisionState.structurally_non_executable,
                reason="intake hints conflict with the canonical external Action Intent payload",
                matched_rule_id=None,
                trace=[{"type": "hard_rule", "matched": True, "reason": "intake_payload_mismatch"}],
                policy=None,
                approval_requirement=None,
                evidence_requirement=None,
            )

        if action_intent.get("source_account_ref") == action_intent.get("destination_account_ref"):
            return PolicyDecision(
                state=DecisionState.structurally_non_executable,
                reason="source and destination accounts must differ",
                matched_rule_id=None,
                trace=[
                    {
                        "type": "hard_rule",
                        "matched": True,
                        "reason": "same_source_and_destination_account",
                    }
                ],
                policy=None,
                approval_requirement=None,
                evidence_requirement=None,
            )

        if policy is None:
            return PolicyDecision(
                state=DecisionState.deny,
                reason="no active tenant workflow policy is available",
                matched_rule_id=None,
                trace=[{"type": "policy_lookup", "matched": False, "reason": "no_active_policy"}],
                policy=None,
                approval_requirement=None,
                evidence_requirement=None,
            )

        action_type = action_intent.get("action_type")
        if policy.finance_action_classes and action_type not in policy.finance_action_classes:
            return PolicyDecision(
                state=DecisionState.deny,
                reason="active policy does not permit this finance action class",
                matched_rule_id=None,
                trace=[
                    {
                        "type": "policy_scope",
                        "matched": False,
                        "reason": "finance_action_class_not_permitted",
                        "expected": policy.finance_action_classes,
                        "actual": action_type,
                    }
                ],
                policy=policy,
                approval_requirement=None,
                evidence_requirement=None,
            )

        sources = {
            "action_intent": action_intent,
            "context": evaluation_context,
            "intake": intake_context,
        }
        trace: list[dict[str, Any]] = []

        ordered_rules = sorted(
            enumerate(policy.rules or []),
            key=lambda item: (item[1].get("priority", 1000), item[0]),
        )
        for _, rule in ordered_rules:
            condition_results = [
                self._evaluate_condition(condition, sources)
                for condition in rule.get("all_conditions", [])
            ]
            matched = all(result["matched"] for result in condition_results)
            trace_entry = {
                "type": "policy_rule",
                "rule_id": rule.get("rule_id"),
                "priority": rule.get("priority", 1000),
                "decision": rule.get("decision"),
                "matched": matched,
                "conditions": condition_results,
            }
            trace.append(trace_entry)
            if matched:
                decision = DecisionState(rule["decision"])
                return PolicyDecision(
                    state=decision,
                    reason=f"policy rule '{rule['rule_id']}' matched",
                    matched_rule_id=rule["rule_id"],
                    trace=trace,
                    policy=policy,
                    approval_requirement=self._approval_requirement_for_rule(rule, decision),
                    evidence_requirement=self._evidence_requirement_for_rule(rule, decision),
                )

        trace.append(
            {
                "type": "policy_default",
                "matched": True,
                "decision": policy.default_decision.value,
                "reason": "no policy rule matched; default decision applied",
            }
        )
        return PolicyDecision(
            state=policy.default_decision,
            reason="no policy rule matched; default decision applied",
            matched_rule_id=None,
            trace=trace,
            policy=policy,
            approval_requirement=self._approval_requirement_for_rule({}, policy.default_decision),
            evidence_requirement=self._evidence_requirement_for_rule({}, policy.default_decision),
        )

    def _evaluate_condition(
        self,
        condition: dict[str, Any],
        sources: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        source_name = condition["source"]
        field_path = condition["field"]
        operator = condition["operator"]
        expected = condition.get("value")
        actual = self._resolve_path(sources.get(source_name, {}), field_path)
        matched = self._apply_operator(operator=operator, actual=actual, expected=expected)
        return {
            "source": source_name,
            "field": field_path,
            "operator": operator,
            "expected": expected,
            "actual": actual,
            "matched": matched,
        }

    def _resolve_path(self, source: dict[str, Any], field_path: str) -> Any:
        current: Any = source
        for segment in field_path.split("."):
            if not isinstance(current, dict) or segment not in current:
                return None
            current = current[segment]
        return current

    def _apply_operator(self, *, operator: str, actual: Any, expected: Any) -> bool:
        if operator == "equals":
            return actual == expected
        if operator == "not_equals":
            return actual != expected
        if operator == "gte":
            return actual is not None and actual >= expected
        if operator == "gt":
            return actual is not None and actual > expected
        if operator == "lte":
            return actual is not None and actual <= expected
        if operator == "lt":
            return actual is not None and actual < expected
        if operator == "in":
            return isinstance(expected, list) and actual in expected
        if operator == "contains":
            if isinstance(actual, list):
                return expected in actual
            if isinstance(actual, str):
                return isinstance(expected, str) and expected in actual
            return False
        if operator == "exists":
            expected_bool = True if expected is None else bool(expected)
            return (actual is not None) is expected_bool
        raise PolicyStateError(f"unsupported policy operator '{operator}'")

    def _approval_requirement_for_rule(
        self,
        rule: dict[str, Any],
        decision: DecisionState,
    ) -> dict[str, Any] | None:
        requirement = rule.get("approval_requirement")
        if requirement:
            return {
                "required_decision_count": max(
                    int(requirement.get("required_decision_count", 1)),
                    1,
                ),
                "eligible_principal_ids": list(requirement.get("eligible_principal_ids", [])),
                "eligible_role_ids": list(requirement.get("eligible_role_ids", [])),
                "approval_group_key": requirement.get("approval_group_key") or rule.get("rule_id"),
                "expires_in_seconds": requirement.get("expires_in_seconds"),
                "require_requester_separation": requirement.get(
                    "require_requester_separation",
                    True,
                ),
                "require_distinct_approvers": requirement.get(
                    "require_distinct_approvers",
                    True,
                ),
            }
        if decision != DecisionState.approval_required:
            return None
        return {
            "required_decision_count": 1,
            "eligible_principal_ids": [],
            "eligible_role_ids": [],
            "approval_group_key": rule.get("rule_id"),
            "expires_in_seconds": None,
            "require_requester_separation": True,
            "require_distinct_approvers": True,
        }

    def _evidence_requirement_for_rule(
        self,
        rule: dict[str, Any],
        decision: DecisionState,
    ) -> dict[str, Any] | None:
        requirement = rule.get("evidence_requirement")
        if requirement:
            return {
                "minimum_count": max(int(requirement.get("minimum_count", 1)), 1),
                "allowed_evidence_types": list(requirement.get("allowed_evidence_types", [])),
                "expires_in_seconds": requirement.get("expires_in_seconds"),
            }
        if decision != DecisionState.needs_evidence:
            return None
        return {
            "minimum_count": 1,
            "allowed_evidence_types": [],
            "expires_in_seconds": None,
        }
