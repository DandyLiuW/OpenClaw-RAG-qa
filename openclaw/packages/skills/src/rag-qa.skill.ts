import { Skill, SkillExecuteParams, SkillMatchParams } from "@openclaw/core";
import axios from "axios";

/**
 * OpenClaw RAG知识库问答技能
 * 匹配关键词：查文档、知识库、文档里、文档中
 * 调用本地RAG服务实现精准问答
 */
export class RagQaSkill implements Skill {
  // Skill唯一标识
  public readonly id = "rag-qa";
  // 技能名称
  public readonly name = "知识库问答";
  // 技能描述
  public readonly description = "查询本地知识库文档，支持PDF/Markdown/TXT等格式，返回带来源的精准答案";
  // RAG服务地址（支持环境变量配置）
  private readonly ragServiceUrl = process.env.RAG_SERVICE_URL || "http://localhost:8000";

  /**
   * 匹配用户指令
   * @param params 包含用户输入内容的参数
   * @returns 是否匹配成功
   */
  async match(params: SkillMatchParams): Promise<boolean> {
    if (!params.content || params.content.trim() === "") {
      return false;
    }
    // 转为小写，提高匹配率
    const userInput = params.content.toLowerCase();
    // 触发关键词列表
    const triggerWords = ["查文档", "知识库", "文档里", "文档中", "查知识库"];
    // 只要包含任意一个关键词就触发
    return triggerWords.some(word => userInput.includes(word));
  }

  /**
   * 执行问答逻辑
   * @param params 包含用户输入的参数
   * @returns 格式化的回答结果
   */
  async execute(params: SkillExecuteParams): Promise<string> {
    try {
      // 1. 清洗用户输入（移除触发关键词）
      let question = params.content
        .replace(/查文档|知识库|文档里|文档中|查知识库/g, "")
        .trim();
      
      // 2. 校验问题是否为空
      if (!question) {
        return "❌ 请告诉我你想查询的具体问题，例如：\n'查文档 项目部署步骤'\n'知识库 报销政策'";
      }

      // 3. 调用RAG服务
      console.log(`📡 调用RAG服务：${this.ragServiceUrl}/query?question=${encodeURIComponent(question)}`);
      const response = await axios.get(`${this.ragServiceUrl}/query`, {
        params: {
          question,
          top_k: 3
        },
        timeout: 30000 // 30秒超时
      });

      // 4. 处理返回结果
      const data = response.data;
      if (data.status !== "success") {
        return `❌ 知识库查询失败：${data.message || "未知错误"}`;
      }

      // 5. 格式化回答（带来源信息）
      let result = `📚 知识库回答：\n${data.answer}\n\n`;
      
      // 添加来源信息
      if (data.sources && data.sources.length > 0) {
        result += "🔍 参考来源：\n";
        data.sources.forEach((source: any, index: number) => {
          result += `${index + 1}. 文件：${source.file_name} | 页码：${source.page_label} | 相似度：${source.similarity_score}%\n`;
        });
      } else {
        result += "🔍 参考来源：无\n";
      }

      return result;

    } catch (error) {
      // 异常处理
      console.error("❌ RAG技能执行失败：", error);
      
      if (axios.isAxiosError(error)) {
        if (error.code === "ECONNREFUSED") {
          return "❌ 无法连接到RAG服务，请检查：\n1. RAG服务是否启动\n2. 服务地址是否正确（当前：${this.ragServiceUrl}）";
        }
        if (error.response) {
          return `❌ 知识库查询失败：${error.response.data.detail || error.message}`;
        }
        return `❌ 网络请求失败：${error.message}`;
      }

      return `❌ 执行异常：${(error as Error).message}`;
    }
  }
}

// 导出Skill实例
export const skill = new RagQaSkill();