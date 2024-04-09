export type PipelineResult = "success" | "failure" | "timed_out";

export type PipelineTriggerSource = "github" | "openapi_hub";

export type PipelineRun = {
  source: PipelineTriggerSource;
  unifiedPipelineTaskKey: string; // a unified pipeline task key, e.g. LintDiff, Semantic
  unifiedPipelineBuildId: string; // a unique build id unified pipeline assigned for each completed pipeline build id
  pipelineBuildId: string; // the id of the record for the completed azure pipeline build.
  pipelineJobId: string; // the id of the record for the completed azure pipeline job.
  pipelineTaskId: string; // the id of the record for the completed azure pipeline task.
  logUrl: string; // the log url of the underlying azure pipeline
};

export type PipelineStatus = "queued" | "in_progress" | "completed";

export type InProgressEvent = PipelineRun & {
  status: "in_progress";
};

export type CompletedEvent = PipelineRun & {
  status: "completed";
  result: PipelineResult;
  logPath: string;
};

export type PipelineEvent = InProgressEvent | CompletedEvent;
