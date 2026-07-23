
import enum
import json
import os
import random
import re
import sys
import threading
import time

import pyaudio
from deepgram import DeepgramClient
from deepgram.agent.v1.types import (
    AgentV1Settings, AgentV1SettingsAgent,
    AgentV1SettingsAgentListen, AgentV1SettingsAgentListenProvider_V1,
    AgentV1SettingsAudio, AgentV1SettingsAudioInput, AgentV1SettingsAudioOutput,
)
from deepgram.types.think_settings_v1 import ThinkSettingsV1
from deepgram.types.think_settings_v1provider import ThinkSettingsV1Provider_OpenAi
from deepgram.types.speak_settings_v1 import SpeakSettingsV1
from deepgram.types.speak_settings_v1provider import SpeakSettingsV1Provider_Deepgram
from deepgram.core.events import EventType



from pathlib import Path
from dotenv import load_dotenv

# verifiacion de la api key

env_path = Path('.env')


load_dotenv()

#verificar que la api que el directorio .venv existe
if not env_path.exists():
    raise FileNotFoundError("The .env file containing the environment variables was not found")

load_dotenv(env_path)

API_KEY = os.getenv("API_KEY")

#verificar que la api key exista
if not API_KEY:
    raise ValueError("The API_KEY variable is not defined in the .env file")

print("API_KEY loaded successfully")
#####

OUTPUT_SAMPLE_RATE = 24000  # typical sample rate for aura-2 voices

# ---------------------------------------------------------------------------
# LEAD DATA (this can later be parameterized / read from a CRM, etc.)
# ---------------------------------------------------------------------------
# LEAD_ID and CALL_ID are now random integers in [1, 15], as requested.
# They're generated once per script run and used consistently below.
LEAD_ID = str(random.randint(1, 15))
CALL_ID = str(random.randint(1, 15))

COMPANY_NAME = "Supercomputadorascuanticas"
CONTACT_NAME = "Edwin Montilla"
INDUSTRY = "Tecnología"

# Project base folder (where this script lives) -> the JSON is saved here.
# The output JSON now includes both lead_id and call_id.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JSON_PATH = os.path.join(BASE_DIR, f"jsons/call_result_{LEAD_ID}_{CALL_ID}.json")

# Spoken text: kept in Spanish on purpose, since the agent talks to a
# Spanish-speaking lead and must introduce itself in Spanish.
GREETING_TEXT = (
    f"Buenos días, ¿es usted el señor {CONTACT_NAME}? "
    f"Le llamo de parte de {COMPANY_NAME} para consultar si está interesado "
    f"en nuestros productos del sector {INDUSTRY}."
)

AGENT_PROMPT = (
    "Eres un agente telefónico de ventas. Tu única tarea en esta llamada es "
    "preguntar si la persona está interesada en nuestros productos y esperar "
    "su respuesta. En cuanto la persona responda con un sí o un no (o algo "
    "equivalente), agradece brevemente y despídete de forma cordial y breve. "
    "No hagas más preguntas ni ofrezcas más información."
)

# ---------------------------------------------------------------------------
# ALLOWED VALUES — enforced with real Enums (not plain strings), so it is
# not possible to write any value outside this exact list into the output
# JSON. These mirror the same Enums used by the persistence layer
# (lead_agent.py's CallState / LeadClassification / LeadInterestLevel).
# Each Enum inherits from str, so its members serialize as plain strings
# in json.dump without any extra encoder.
# ---------------------------------------------------------------------------

class CallState(str, enum.Enum):
    ANSWERED = "CONTESTADA"
    BUSY = "OCUPADO"
    VOICEMAIL = "BUZON_DE_VOZ"
    INVALID_NUMBER = "NUMERO_INVALIDO"
    NO_ANSWER = "NO_CONTESTA"
    NETWORK_ERROR = "ERROR_RED"


class LeadClassification(str, enum.Enum):
    HOT_LEAD = "HOT_LEAD"
    WARM_LEAD = "WARM_LEAD"
    COLD_LEAD = "COLD_LEAD"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"
    NO_CONTACTADO = "NO_CONTACTADO"
    RESPUESTA_AMBIGUA = "RESPUESTA_AMBIGUA"


class LeadInterestLevel(str, enum.Enum):
    HIGH = "ALTO"
    MEDIUM = "MEDIO"
    LOW = "BAJO"
    REJECTED = "RECHAZADO"
    NONE = "NULO"


def validate_result_payload(payload):
    """Defensive final check: raises if call_state, lead_classification, or
    lead_interest_level is ever anything other than one of the allowed
    values, even if this code is edited later or reused elsewhere."""
    try:
        CallState(payload["call_state"])
        LeadClassification(payload["lead_classification"])
        LeadInterestLevel(payload["lead_interest_level"])
    except ValueError as e:
        raise ValueError(f"Invalid value in the result payload: {e}")

# ---------------------------------------------------------------------------
# STATE SHARED BETWEEN THREADS
# ---------------------------------------------------------------------------
state_lock = threading.Lock()
lead_classification = None     # LeadClassification.HOT_LEAD | LeadClassification.COLD_LEAD | None
classification_reason = ""
user_response_text = ""
transcript = []                # list of {"role": ..., "content": ...}
call_finished_event = threading.Event()

# Spanish keyword lists: kept in Spanish since they match what a
# Spanish-speaking lead actually says out loud.
POSITIVE_KEYWORDS = [
    "si", "sí", "claro", "por supuesto", "me interesa", "interesado",
    "interesada", "dale", "bueno", "afirmativo",
]
NEGATIVE_PHRASES = [
    "no me interesa", "no estoy interesado", "no estoy interesada",
    "no gracias", "para nada", "no por ahora", "no, gracias",
]


def get_field(obj, name, default=None):
    """Defensive attribute/key access, since the SDK may return typed
    objects or plain dicts depending on the version."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def classify_response(text):
    """Determines HOT_LEAD/COLD_LEAD from the user's spoken response."""
    global lead_classification, classification_reason, user_response_text

    with state_lock:
        if lead_classification is not None:
            return  # already classified, don't re-evaluate

        text_lower = text.lower().strip()
        words = re.findall(r"\w+", text_lower)

        is_negative = any(neg in text_lower for neg in NEGATIVE_PHRASES) or (
            words and words[0] in ("no", "nel", "nop")
        )
        is_positive = any(pos in text_lower for pos in POSITIVE_KEYWORDS)

        if is_negative:
            lead_classification = LeadClassification.COLD_LEAD
            classification_reason = "El contacto indicó explícitamente que no está interesado en los productos ofrecidos."
        elif is_positive:
            lead_classification = LeadClassification.HOT_LEAD
            classification_reason = "El contacto indicó explícitamente que sí está interesado en los productos ofrecidos."
        else:
            return  # ambiguous response, keep waiting for a clearer one

        user_response_text = text
        call_finished_event.set()


def build_settings():
    """Builds the settings object, with a fallback in case the installed
    SDK version doesn't support the 'greeting' kwarg on AgentV1SettingsAgent."""
    common_kwargs = dict(
        listen=AgentV1SettingsAgentListen(
            provider=AgentV1SettingsAgentListenProvider_V1(type="deepgram", model="nova-3", language="es")
        ),
        think=ThinkSettingsV1(
            provider=ThinkSettingsV1Provider_OpenAi(type="open_ai", model="gpt-4o-mini"),
            prompt=AGENT_PROMPT,
        ),
        speak=SpeakSettingsV1(
            provider=SpeakSettingsV1Provider_Deepgram(type="deepgram", model="aura-2-nestor-es")
        ),
    )

    try:
        agent_cfg = AgentV1SettingsAgent(greeting=GREETING_TEXT, **common_kwargs)
    except TypeError:
        # This SDK version doesn't expose 'greeting' as a direct kwarg;
        # we continue anyway, the greeting will be handled by the
        # prompt/first turn instead.
        print("Notice: this SDK does not support a direct 'greeting' field, skipping it.")
        agent_cfg = AgentV1SettingsAgent(**common_kwargs)

    return AgentV1Settings(
        audio=AgentV1SettingsAudio(
            input=AgentV1SettingsAudioInput(encoding="linear16", sample_rate=16000),
            output=AgentV1SettingsAudioOutput(
                encoding="linear16",
                sample_rate=OUTPUT_SAMPLE_RATE,
                container="none",
            ),
        ),
        agent=agent_cfg,
    )


def save_result():
    """Builds and saves the final JSON with the call result, following the
    lead_id / call_id / call_state / lead_classification / lead_interest_level /
    classification_reason / recommended_next_action / observations format.
    Both lead_id and call_id are random integers assigned at the start of
    this run (see LEAD_ID / CALL_ID above)."""

    if lead_classification == LeadClassification.HOT_LEAD:
        interest_level = LeadInterestLevel.HIGH
        next_action = "Agendar seguimiento comercial con el contacto"
        final_classification = LeadClassification.HOT_LEAD
        reason = classification_reason
    elif lead_classification == LeadClassification.COLD_LEAD:
        interest_level = LeadInterestLevel.LOW
        next_action = "Descartar lead / no dar seguimiento por ahora"
        final_classification = LeadClassification.COLD_LEAD
        reason = classification_reason
    else:
        # The call ended without a clear yes/no from the contact.
        interest_level = LeadInterestLevel.NONE
        next_action = "Reintentar el contacto en otro momento con una pregunta más directa"
        final_classification = LeadClassification.RESPUESTA_AMBIGUA
        reason = "La llamada finalizó sin una respuesta clara de interés por parte del contacto."

    observations_payload = {
        "company_name": COMPANY_NAME,
        "contact_name": CONTACT_NAME,
        "industry": INDUSTRY,
        "user_text_response": user_response_text,
        "transcript": transcript,
    }

    result_payload = {
        "lead_id": LEAD_ID,
        "call_id": CALL_ID,
        "call_state": CallState.ANSWERED,
        "lead_classification": final_classification,
        "lead_interest_level": interest_level,
        "classification_reason": reason,
        "recommended_next_action": next_action,
        "observations": observations_payload,
    }

    # Hard guarantee: this raises before anything is written to disk if any
    # of the three restricted fields is ever not one of the allowed values.
    validate_result_payload(result_payload)

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, ensure_ascii=False, indent=2)

    print("\n--- Generated JSON ---")
    print(json.dumps(result_payload, ensure_ascii=False, indent=2))
    print(f"\nSaved to: {OUTPUT_JSON_PATH}")
    print("\nExecution finished successfully")


def main():
    client = DeepgramClient(api_key=API_KEY)

    audio = pyaudio.PyAudio()

    # INPUT stream (microphone)
    input_stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1024
    )

    # OUTPUT stream (speakers) — to play back the agent's voice
    output_stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=OUTPUT_SAMPLE_RATE,
        output=True
    )

    print(f"Lead ID: {LEAD_ID} | Call ID: {CALL_ID}")
    print("Connecting to the Agent...")

    try:
        with client.agent.v1.connect() as agent:
            print("Connected to the WebSocket!")

            settings = build_settings()

            def on_message(message):
                # Audio coming back arrives as raw bytes; everything else is a JSON event.
                if isinstance(message, (bytes, bytearray)):
                    output_stream.write(bytes(message))
                    return

                msg_type = get_field(message, "type")

                if msg_type == "ConversationText":
                    role = get_field(message, "role")
                    content = get_field(message, "content", "") or ""
                    transcript.append({"role": role, "content": content})
                    print(f"[{role}] {content}")

                    if role == "user":
                        classify_response(content)
                else:
                    print(f"Agent event: {message}")

            agent.on(EventType.OPEN, lambda _: print("Connection opened"))
            agent.on(EventType.MESSAGE, on_message)
            agent.on(EventType.CLOSE, lambda _: print("Connection closed"))
            agent.on(EventType.ERROR, lambda err: print(f"Socket error: {err}"))

            agent.send_settings(settings)

            listen_thread = threading.Thread(target=agent.start_listening, daemon=True)
            listen_thread.start()

            print("Calling... simulating a phone dial. (Ctrl+C to exit)")

            # Main loop: we keep sending audio until the classification
            # (hot/cold) is detected from the user's response.
            while not call_finished_event.is_set():
                data = input_stream.read(1024, exception_on_overflow=False)
                agent.send_media(data)

            # Small buffer so we don't cut off the closing/farewell audio.
            time.sleep(1.5)

    except KeyboardInterrupt:
        print("\nStream stopped by the user.")
    except Exception as e:
        print(f"Critical error: {e}")
    finally:
        input_stream.stop_stream()
        input_stream.close()
        output_stream.stop_stream()
        output_stream.close()
        audio.terminate()
        print("Resources closed correctly.")

        with state_lock:
            if lead_classification is None:
                # Leave it as None here; save_result() already handles the
                # "no clear answer" case as RESPUESTA_AMBIGUA.
                pass

        save_result()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)