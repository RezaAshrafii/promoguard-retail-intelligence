export type ScenarioRequestBuildResult =
  | { ok: false; errors: string[] }
  | { ok: true; payload: Record<string, unknown>; json: string };

export function buildScenarioRequest(form: Record<string, string>): ScenarioRequestBuildResult;
