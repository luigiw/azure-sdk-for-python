export type MessageLevel = "Info" | "Warning" | "Error";

export type JsonPath = {
  tag: string; // meta info about the path, e.g. "swagger" or "example"
  path: string;
};

export type MesssageContext = {
  toolVersion: string; 
}

export type Extra = {
  [key: string]: any;
};

export type BaseMessageRecord = {
  level: MessageLevel;
  message: string;
  time: Date;
  context?: MesssageContext;
  extra?: Extra;
};

export type ResultMessageRecord = BaseMessageRecord & {
  type: "Result";
  id?: string;
  code?: string;
  docUrl?: string;
  paths: JsonPath[];
};

export type RawMessageRecord = BaseMessageRecord & {
  type: "Raw";
};

export type MessageRecord = ResultMessageRecord | RawMessageRecord 

export type MessageLine = MessageRecord | MessageRecord[]
