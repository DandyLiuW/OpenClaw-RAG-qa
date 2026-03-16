import { Skill } from "@openclaw/core";
// 导入默认技能（保留原有技能）
import { skill as echoSkill } from "./skills/echo.skill";
import { skill as helpSkill } from "./skills/help.skill";
// 导入自定义RAG技能
import { skill as ragQaSkill } from "./skills/rag-qa.skill";

// 注册所有技能
export const skills: Skill[] = [
  echoSkill,
  helpSkill,
  ragQaSkill // 新增RAG问答技能
];