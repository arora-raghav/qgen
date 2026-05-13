import json
import random
import logging
import time

from ..generation_agent import generation_agent
from .depth import createConstraintsPrompt, createDeepenPrompt, createConcretizingPrompt, createReasoningPrompt
from .breadth import createBreadthPrompt
from ...configuration import CONFIGURATION

logger = logging.getLogger(__name__)

def evolve_dataset(dataset):
    logger.info(f"🧬 Starting evolution process with {len(dataset)} records...")
    evolution_start_time = time.time()
    
    current_dataset = dataset
    for evolution_round in range(CONFIGURATION["evolution_depth"]):
        round_start_time = time.time()
        logger.info(f"🔄 Evolution round {evolution_round + 1}/{CONFIGURATION['evolution_depth']} starting...")
        
        evolved_dataset = []
        for record_index, dataset_row in enumerate(current_dataset):
            record_start_time = time.time()
            logger.debug(f"Processing record {record_index + 1}/{len(current_dataset)} in round {evolution_round + 1}")
            
            try:
                dataset_row_json = json.dumps([dataset_row])
                
                # Create evolution prompts
                logger.debug("Creating evolution prompts...")
                evol_prompts = []
                evol_prompts.append(createConstraintsPrompt(dataset_row_json))
                evol_prompts.append(createDeepenPrompt(dataset_row_json))
                evol_prompts.append(createConcretizingPrompt(dataset_row_json))
                evol_prompts.append(createReasoningPrompt(dataset_row_json))
                evol_prompts.append(createBreadthPrompt(dataset_row_json))

                selected_evol_prompt = random.choice(evol_prompts)
                logger.debug(f"Selected evolution strategy for record {record_index + 1}")
                
                # This is where it likely hangs - the API call
                logger.info(f"🤖 Making evolution API call for record {record_index + 1}...")
                api_start_time = time.time()
                
                evolved_dataset_row = generation_agent(
                    selected_evol_prompt, 
                    system_prompt="Always return the same schema as the input dataset no matter what so that it can be parsed later."
                )
                
                api_time = time.time() - api_start_time
                logger.info(f"✅ Evolution API call completed for record {record_index + 1} in {api_time:.2f}s")
                
                if evolved_dataset_row:
                    evolved_dataset.extend(evolved_dataset_row)
                    logger.debug(f"Record {record_index + 1} evolved successfully")
                else:
                    logger.warning(f"Record {record_index + 1} evolution returned empty result")
                    
            except Exception as record_error:
                logger.error(f"❌ Failed to evolve record {record_index + 1}: {record_error}")
                continue
            
            record_time = time.time() - record_start_time
            logger.debug(f"Record {record_index + 1} processing completed in {record_time:.2f}s")
            
        dataset.extend(evolved_dataset)
        if evolved_dataset:
            current_dataset = evolved_dataset
            logger.info(f"Evolution round {evolution_round + 1} produced {len(evolved_dataset)} new records")
        else:
            logger.warning(f"Evolution round {evolution_round + 1} produced no new records, using previous dataset for next round")
        
        round_time = time.time() - round_start_time
        logger.info(f"✅ Evolution round {evolution_round + 1} completed: {len(evolved_dataset)} new records in {round_time:.2f}s")
        
    total_time = time.time() - evolution_start_time
    logger.info(f"🎉 Evolution process completed: {len(dataset)} total records in {total_time:.2f}s")
    
    return dataset



	




