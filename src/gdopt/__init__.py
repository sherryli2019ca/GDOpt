"""GDOpt: strength reduction for LLM agents.

Pipeline (see docs/design): traces -> situations -> profile -> shadow/replay
-> tier table + calibrated threshold -> tiered policy.
"""

from .calibrate import CalibrationResult, learn_then_test, risk_curve
from .decision import CachedDecisionModel, FunctionDecisionModel, OpenRouterJev, action_menu, conversation_state
from .entities import EntitySchema, EntityTable, build_entity_table
from .profile import ProfileReport, SituationProfile, candidate_tiers, fit_situations, profile, split_by_trial
from .replay import EpisodeResult, EvalSummary, Runner, counterfactual_sensitivity, evaluate
from .shadow import ShadowResult, shadow_evaluate
from .situation import SituationModel, SituationTree, featurize
from .tiers import Decision, Tier, TieredPolicy, TierRule, TierTable
from .trace import Message, Step, ToolCall, Trajectory, all_steps

__all__ = [
    "CalibrationResult", "learn_then_test", "risk_curve",
    "CachedDecisionModel", "FunctionDecisionModel", "OpenRouterJev", "action_menu", "conversation_state",
    "EntitySchema", "EntityTable", "build_entity_table",
    "ProfileReport", "SituationProfile", "candidate_tiers", "fit_situations", "profile", "split_by_trial",
    "EpisodeResult", "EvalSummary", "Runner", "counterfactual_sensitivity", "evaluate",
    "ShadowResult", "shadow_evaluate",
    "SituationModel", "SituationTree", "featurize",
    "Decision", "Tier", "TieredPolicy", "TierRule", "TierTable",
    "Message", "Step", "ToolCall", "Trajectory", "all_steps",
]
