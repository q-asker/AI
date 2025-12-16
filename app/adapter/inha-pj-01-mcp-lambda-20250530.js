process.env.HOME = "./tmp";

import { ConverseCommand } from "@aws-sdk/client-bedrock-runtime";
import { SendMessageCommand } from "@aws-sdk/client-sqs";
import { randomUUID } from "crypto";
import {
  bedrockClient,
  mcpClient,
  redisClient,
  sqsClient,
} from "./client/index.mjs";
import { toolConfig, toolDescription } from "./config/toolConfig.mjs";

export const handler = async (event) => {
  const records = event.Records;
  const results = await Promise.allSettled(records.map(runByEachRecord));

  results.forEach((result, idx) => {
    if (result.status === "rejected") {
      console.error(`레코드 ${idx} 처리 중 에러 발생:`, result.reason);
    }
  });

  return {
    batchItemFailures: [],
  };
};

const runByEachRecord = async (record) => {
  const promptKey = record.body;
  const messageGroupId = promptKey.split(":")[1];
  const prompt = await redisClient.get(promptKey);
  const prompt_json = JSON.parse(prompt);

  const { modelId, body } = prompt_json;

  const { max_tokens, system, messages } = body;

  const inferenceConfig = {
    max_tokens: max_tokens,
    top_p: 0.1,
    temperature: 0.3,
  };

  const command = new ConverseCommand({
    modelId: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages,
    system: [
      {
        text:
          system +
          "\n\n" +
          `You are a helpful assistant. You have access to the following tools.: ${JSON.stringify(
            toolDescription
          )}`,
      },
    ],
    inferenceConfig,
    toolConfig,
  });

  const response = await bedrockClient.send(command);
  const { output, stopReason } = response;
  const { message: outputMessage } = output;
  messages.push(outputMessage);
  console.log("outputMessage", outputMessage);
  if (stopReason !== "tool_use") {
    await finishConversation(promptKey, outputMessage);
    return;
  }

  const toolRequests = outputMessage.content;
  for (const toolRequest of toolRequests) {
    const toolUse = toolRequest.toolUse;
    if (!toolUse) {
      continue;
    }
    const toolResult = await getToolResult(toolRequest.toolUse);
    console.log("searched result:", toolResult);
    messages.push({
      role: "user",
      content: [{ toolResult: toolResult }],
    });
  }
  prompt_json.body.messages = messages;
  await redisClient.set(promptKey, JSON.stringify(prompt_json));
  await sqsClient.send(
    new SendMessageCommand({
      QueueUrl:
        "https://sqs.us-east-1.amazonaws.com/730335373015/inha-pj-01-to-mcp-sqs-20250522.fifo",
      MessageBody: promptKey,
      MessageGroupId: messageGroupId,
      MessageDeduplicationId: randomUUID(),
    })
  );
  console.log("sent message to sqs");
  return;
};

const getToolResult = async (toolUse) => {
  const { toolUseId, name, input } = toolUse;
  try {
    const toolResponse = await mcpClient.callTool({
      name: name,
      arguments: input,
    });
    return {
      toolUseId,
      content: toolResponse.content,
    };
  } catch (error) {
    return {
      toolUseId,
      content: [{ text: `Error: ${String(error.message)}` }],
      status: "error",
    };
  }
};

const finishConversation = async (promptKey, outputMessage) => {
  const messageGroupId = promptKey.split(":")[1];
  const publishKey = "notify:" + messageGroupId;
  await redisClient.publish(
    publishKey,
    JSON.stringify({
      sequence: promptKey.split(":")[2],
      generated_text: outputMessage.content[0].text,
    })
  );
  return;
};