#I'm buidlig a template for ai voice agent product for call center automation
 
 
import os
from pathlib import Path
 
project_name= "src"
 
list_of_files= [
 
      f"{project_name}/__init__.py",
 
        f"{project_name}/components/__init__.py",
        f"{project_name}/components/call_logger.py",
        f"{project_name}/components/transcription_logger.py",
        f"{project_name}/components/masking.py",
        f"{project_name}/components/language_agent.py",
        f"{project_name}/components/confidence.py",
        f"{project_name}/components/masking.py",
        f"{project_name}/components/transfer_agent.py",
        f"{project_name}/components/speaker_verification.py",
 
 
        f"{project_name}/agentic_rag/__init__.py",
        f"{project_name}/agentic_rag/knowledge_base.py",
        f"{project_name}/agentic_rag/memory_manager.py",
        f"{project_name}/agentic_rag/retriever_tool.py",
        f"{project_name}/agentic_rag/route_tool.py",
        f"{project_name}/agentic_rag/generation_tool.py",
 
        f"{project_name}/prompts/__init__.py",
        f"{project_name}/prompts/type_of_prompts.py",
        f"{project_name}/prompts/prompt_aivoice_agent.py",
 
        f"{project_name}/pipeline/__init__.py",
        f"{project_name}/pipeline/voice_agent_pipeline.py",
        f"{project_name}/pipeline/agentic_rag_pipeline.py",
        f"{project_name}/pipeline/sentiment_analysis_pipeline.py",
        f"{project_name}/pipeline/transcription_pipeline.py",
 
        f"{project_name}/constant/__init__.py",
        f"{project_name}/constant/constant.py",
 
        f"{project_name}/exception/__init__.py",
 
        f"{project_name}/logger/__init__.py",
 
        f"{project_name}/utils/__init__.py",
        f"{project_name}/utils/main_utils.py",
 
        f"{project_name}/entity/__init__.py",
        f"{project_name}/entity/entity_model_config.py",
        f"{project_name}/entity/artifact_entity.py",
 
         "app.py",
         "requirements.txt",
         "Dockerfile",
         ".dockerignore",
         "demo.py",
         "main.py",
         "setup.py",
 
         "config/models.json",
         "config/behavior.json",
         "config/model_settings.json"
         
 
]
 
for filepath in list_of_files:
    filepath=Path(filepath)
 
    filedir,filename=os.path.split(filepath)
    if filedir !="":
        os.makedirs(filedir,exist_ok=True)
    if (not os.path.exists(filename)) or (os.path.getsize(filepath)==0):
        with open(filepath,"w") as f:
            pass
    else:
        print(f"file is already presented at :{filepath}")