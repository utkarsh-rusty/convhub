from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID

from app.models.enums import (
    PricingProfileType,
    ProviderSimulationMode,
    RoutingOverrideMode,
)


@dataclass(frozen=True)
class DemoRuntimeContext:
    workspace_id: UUID
    pricing_profile: PricingProfileType
    provider_simulation: ProviderSimulationMode
    routing_override_mode: RoutingOverrideMode
    routing_override_account_id: UUID | None


_demo_runtime: ContextVar[DemoRuntimeContext | None] = ContextVar("demo_runtime", default=None)


def set_demo_runtime(context: DemoRuntimeContext | None) -> Token | None:
    if context is None:
        _demo_runtime.set(None)
        return None
    return _demo_runtime.set(context)


def reset_demo_runtime(token: Token | None) -> None:
    if token is not None:
        _demo_runtime.reset(token)
    else:
        _demo_runtime.set(None)


def get_demo_runtime() -> DemoRuntimeContext | None:
    return _demo_runtime.get()


def get_active_pricing_profile() -> PricingProfileType:
    runtime = get_demo_runtime()
    if runtime is None:
        return PricingProfileType.PRODUCTION
    return runtime.pricing_profile
