from fastapi import FastAPI, UploadFile, File, HTTPException
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.storage.storage_context import StorageContext
import chromadb
from sentence_transformers import SentenceTransformer
import os
import shutil
from typing import List, Optional

# 初始化FastAPI应用
app = FastAPI(
    title="OpenClaw RAG Service",
    description="本地知识库问答服务，支持PDF/Markdown文档解析与检索",
    version="1.0.0"
)

# 创建必要目录
os.makedirs("./uploaded_docs", exist_ok=True)
os.makedirs("./chroma_db", exist_ok=True)

# 配置本地Embedding模型（无需联网）
embed_model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
Settings.embed_model = lambda text: embed_model.encode(text, normalize_embeddings=True)
# 关闭LLM自动加载（仅用Embedding做检索）
Settings.llm = None

# 配置Chroma向量数据库
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_or_create_collection("openclaw_docs")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 全局索引变量
index = None

# 加载本地已有文档（服务启动时自动加载）
def load_existing_docs():
    global index
    if os.listdir("./uploaded_docs"):
        documents = SimpleDirectoryReader("./uploaded_docs").load_data()
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context
        )
        print(f"✅ 已加载 {len(documents)} 个文档片段到向量库")
    else:
        print("⚠️  暂无本地文档，请先上传")

# 启动时加载文档
load_existing_docs()

@app.post("/upload_docs", summary="上传文档到向量库")
async def upload_docs(files: List[UploadFile] = File(...)):
    """
    上传多个PDF/Markdown/TXT文档，加载到向量库
    支持格式：.pdf, .md, .txt
    """
    try:
        uploaded_files = []
        for file in files:
            # 校验文件格式
            allowed_extensions = [".pdf", ".md", ".txt"]
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的文件格式：{file_ext}，仅支持{allowed_extensions}"
                )
            
            # 保存文件
            file_path = f"./uploaded_docs/{file.filename}"
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            uploaded_files.append(file.filename)
        
        # 重新加载文档到向量库
        global index
        documents = SimpleDirectoryReader("./uploaded_docs").load_data()
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context
        )
        
        return {
            "status": "success",
            "message": f"成功上传 {len(uploaded_files)} 个文件",
            "uploaded_files": uploaded_files,
            "total_document_chunks": len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败：{str(e)}")

@app.get("/query", summary="知识库问答")
async def query_docs(
    question: str,
    top_k: Optional[int] = 3  # 返回最相关的3个片段
):
    """
    检索知识库并生成回答
    - question: 查询问题
    - top_k: 返回最相关的文档片段数量（默认3）
    """
    try:
        if index is None:
            raise HTTPException(status_code=400, detail="向量库为空，请先上传文档！")
        
        if not question or question.strip() == "":
            raise HTTPException(status_code=400, detail="查询问题不能为空！")
        
        # 配置查询引擎
        query_engine = index.as_query_engine(
            similarity_top_k=top_k,
            response_mode="compact"  # 紧凑模式返回结果
        )
        
        # 执行查询
        response = query_engine.query(question)
        
        # 提取来源信息
        sources = []
        for node in response.source_nodes:
            sources.append({
                "file_name": node.node.metadata.get("file_name", "未知文件"),
                "page_label": node.node.metadata.get("page_label", "未知页码"),
                "similarity_score": round(node.score * 100, 2),
                "text": node.node.text[:200] + "..." if len(node.node.text) > 200 else node.node.text
            })
        
        return {
            "status": "success",
            "answer": str(response),
            "sources": sources,
            "question": question
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败：{str(e)}")

@app.delete("/clear_docs", summary="清空所有文档和向量库")
async def clear_docs():
    """清空上传的文档和向量库（谨慎使用）"""
    try:
        # 删除上传的文档
        for file in os.listdir("./uploaded_docs"):
            os.remove(os.path.join("./uploaded_docs", file))
        
        # 重置向量库
        global index
        chroma_client.delete_collection("openclaw_docs")
        chroma_collection = chroma_client.create_collection("openclaw_docs")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = None
        
        return {"status": "success", "message": "已清空所有文档和向量库"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败：{str(e)}")

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )