  Training Unmanned Aerial Vehicles (UAVs) to perform complex cooperative tasks through Multi-Agent Reinforcement Learning (MARL) without human involvement is notably challenging.
  To address this challenge, this paper introduces the Task-Activated Language model based Knowledge-Extended Reasoning (TALKER) system, which decomposes complex tasks into learning basic skills and planning with these skills.
  Specifically, we trained three types of fine-grained skills for UAVs, and based on these skills, we constructed a basic action primitive library to accomplish complex multi-vehicle cooperative tasks.
  At the task planning level, we utilize large language models(LLMs) to perform embodied reasoning by
  invoking the action primitive library during interactions with the user. 
  To ensure the accurate comprehension by the LLMs, we have established a prompts library using task types as labels. These prompts are linked to the action primitive library, and users and developers are able to update and maintain them, conveniently. 
  During usage, when users point out potential errors or suboptimal outcomes of the model's output, the system is designed to gradually refine its understanding of the task by leveraging user feedback, and continuously improve its performance accordingly.
  In experiments, we demonstrated the outstanding performance of our system in various drone swarm tasks, such as collaborative search, logistics scheduling, and emergency rescue. 
