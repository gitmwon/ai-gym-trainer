import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
from router import detect_intent
from recommender import recommend_workout
from exercise_launcher import launch_exercise
from rag import get_rag_answer
from faster_whisper import WhisperModel
import json
import tempfile
from fastapi import FastAPI, WebSocket
from fastapi import Body
from pydantic import BaseModel
from fastapi.websockets import WebSocketDisconnect
import asyncio

app = FastAPI()

print("🔥 AI Fitness Trainer Ready!")

model = WhisperModel(
    "base",          # best accuracy
    device="cpu",
    compute_type="int8"  # important for speed on CPU
)
    
@app.websocket("/ws/audio")
async def audio_ws(websocket: WebSocket):
    await websocket.accept()

    audio_buffer = bytearray()

    try:
        while True:
            msg = await websocket.receive()

            # Receive audio chunks
            if msg.get("bytes") is not None:
                audio_buffer.extend(msg["bytes"])

            # When frontend sends stop
            elif msg.get("text") is not None:
                data = json.loads(msg["text"])

                if data.get("type") == "stop":

                    # Save to temp file
                    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                        f.write(audio_buffer)
                        temp_path = f.name

                    segments, info = await asyncio.to_thread(
                        model.transcribe,
                        temp_path,
                        language="en"
                    )

                    transcript = ""
                    for segment in segments:
                        transcript += segment.text   

                    await websocket.send_json({
                    "type": "final_transcript",
                    "text": transcript
                })

                # 2️⃣ Generate trainer reply (LLM)
                #reply = get_rag_answer(transcript)
                intent = detect_intent(transcript)
                if intent == "recommend": 
                    response = recommend_workout() 
                elif intent == "exercise": 
                    response = launch_exercise(transcript) 
                else: 
                    response = get_rag_answer(transcript) 
            
                if intent == "exercise":
                    await websocket.send_json(response)

                # 3️⃣ Send assistant reply
                if intent != "exercise":
                    await asyncio.sleep(0.02)
                    await websocket.send_json({
                        "type": "assistant",
                        "text": response
                    })

                os.remove(temp_path)

                audio_buffer = bytearray()

    except WebSocketDisconnect:
        pass


@app.websocket("/ws/trainer")
async def trainer_ws(websocket: WebSocket):
    print("🔌 Client connected to trainer websocket")
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            user_text = data["message"]
            assistantId = data["assistantId"]

            intent = detect_intent(user_text)
            if intent == "recommend": 
                response = recommend_workout() 
            elif intent == "exercise": 
                response = launch_exercise(user_text) 
            else: 
                response = get_rag_answer(user_text) 
            
            if intent == "exercise":
                await websocket.send_json(response)

            if intent != "exercise":
                for char in response:
                    await asyncio.sleep(0.02)
                    await websocket.send_json({
                        "type": "stream",
                        "token": char,
                        "assistantId": assistantId
                    })
            await websocket.send_json({"type": "done", "assistantId": assistantId})
    except WebSocketDisconnect:
        pass

class Profile(BaseModel):
    height: int
    weight: float
    targetWeight: float
    fitnessGoal: str
    age: int

@app.post("/generate_plan")
async def generate_plan(profile: Profile):
    try:
        age = profile.age
        height = profile.height
        weight = profile.weight
        target_weight = profile.targetWeight
        fitness_goal = profile.fitnessGoal

        prompt = f"""
        You are an expert fitness coach. Your task is to create a structured weekly workout plan tailored to the user's profile and goals.

        STRICT CONSTRAINTS:
        1. Schedule workouts ONLY for Monday through Friday. Saturday and Sunday MUST be rest days.
        2. Assign  4 exercises per workout day.
        3. You MUST ONLY select exercises from the "Available Exercises" list provided below. Do NOT hallucinate, recommend, or include any exercises outside of this list under any circumstances.

        USER PROFILE:
        - Age: {age}
        - Height: {height}
        - Weight: {weight}
        - Target Weight: {target_weight}
        - Fitness Goal: {fitness_goal}

        AVAILABLE EXERCISES:
        mentioned in the fitness trainer's knowledge base

        REQUIRED OUTPUT FORMAT:
        You must recommend the workout plan considering the user's profile and fitness goal, while strictly adhering to the constraints. The plan MUST be formatted EXACTLY as follows, with no deviations:
        You must return the plan exactly in the following format. Do not add any extra conversational text or formatting:
        provide the result in JSON 
        Return ONLY valid JSON.

        The JSON must:
        - Have days of the week as keys
        - Have an array of exercise names as values
        - Contain no explanations
        - Contain no markdown
        - Contain no extra text

        Format exactly like this:

        {{
        "monday": ["Exercise1", "Exercise2","Exercise3","Exercise4"],
        "tuesday": ["Exercise1", "Exercise2","Exercise3","Exercise4"],
        "wednesday": ["Exercise1", "Exercise2","Exercise3","Exercise4"],
        "thursday": ["Exercise1", "Exercise2","Exercise3","Exercise4"],
        "friday": ["Exercise1", "Exercise2","Exercise3","Exercise4"],
        "saturday": ["rest"],
        "sunday": ["rest"]
        }}
        """

        plan = await asyncio.to_thread(get_rag_answer, prompt)

        print("Generated Plan:", plan)
    
        return {
            "success": True,
            "plan": plan,  
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


