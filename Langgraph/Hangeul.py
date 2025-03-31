import streamlit as st
from langgraph.graph import StateGraph
from typing import Dict, List, TypedDict
import json
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import re
from typing import  Dict
from jamo import h2j, j2hcj  
import json

class RobotState(TypedDict):
    text: str
    decomposed_text: List[str]
    available_tools: List[Dict]
    selected_tools: List[Dict]
    adjusted_coordinates: Dict[str, Dict[str, float]]
    generated_code: List[Dict[str, float]]
    result: str
    syllable_lengths: List[int] 
    
# Define Agents
class SelectToolAgent:
    def __init__(self, tools):
        """Initialize the agent with available tools and LLM."""
        self.tools = tools
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.1, max_tokens=200)

    def run(self, decomposed_text: List[str]):
        """Use LLM to select the necessary tools based on decomposed text."""
        prompt = f"""
        You are selecting tools for a robotic arm that draws Hangul characters.

        Given the following Korean consonants and vowels:
        {', '.join(decomposed_text)}

        Match each component **EXACTLY** to one of the tool names from the list below:
        {', '.join([tool['title'] for tool in self.tools])}

        Return **ONLY a valid JSON object** with the adjusted coordinates and nothing else.
        - **DO NOT add explanations or descriptions.**
        - DO NOT include any leading words such as "json", "JSON output", or markdown syntax like ```json.
        - The output must start **only** with '{' and end with '}' — nothing else.
        - The response must be a pure, raw JSON object without code blocks, labels, or surrounding text.
        
        **Example Input & Output:**
        - Input: ['ㄱ', 'ㅏ', 'ㄴ']
        - Available Tools: ㄱ, ㄴ, ㄷ, ㅏ, ㅓ, ㅗ
        - Output: ㄱ, ㅏ, ㄴ
        """

        response = self.llm.invoke([
            SystemMessage(content="You are a tool selection assistant."),
            HumanMessage(content=prompt)
        ])

        selected_tools = [t.strip() for t in response.content.split(",")]

        st.write("[DEBUG] Parsed Selected Tools:", selected_tools)  

        tool_dict = {tool["title"]: tool for tool in self.tools}
        final_tools = [tool_dict[t] for t in selected_tools if t in tool_dict]

        return final_tools

# Node: Modify Coordinates
class ModifyCoordinatesAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model_name="gpt-4", temperature=0.0 , max_tokens=800)

    def run(self, state: Dict[str, any]):
        original_text = state["text"]
        selected_tools = state["selected_tools"]
        tool_names = ", ".join([tool["title"] for tool in selected_tools])
        prompt = f"""
        You are an AI that generates 3D position coordinates for Hangul character components (jamo) to form natural handwriting. Your job is to assign proper [x, y, z] coordinates to each component.

        ---

        ### 💡 TASK OVERVIEW

        Step 1. DO NOT analyze the input text. Use ONLY the given jamo list in order.
        Step 2. Group the jamo components based on the provided syllable lengths.
        Step 3. For each group, identify 초성, 중성, 종성 based on order and vowel list.
        Step 4. Determine the Case (1–4) using both syllable length and vowel direction.
        Step 5. Assign coordinates strictly using the defined Case values.

        ---

        ### 🔠 INPUT TEXT
        - The text to render is: "{original_text}"

        ---

        ### 📋 Selected Jamo Tools (in exact order)
        {tool_names}

        ❗ You MUST use these tools exactly as shown.  
        ❗ DO NOT change or guess characters based on pronunciation or context.  
        ❗ Use only these jamo in the exact given order.

        ---

        ### 🧩 COMPONENT RULES

        초성 and 종성 can only be consonants, while 중성 must be a vowel.  
        A syllable always contains **exactly one vowel**, which is the 중성.  
        - The vowel is always the 중성.
        - The consonant before the vowel is the 초성.
        - If a consonant comes after the vowel, it's the 종성.

        ---

        ### 🧭 VOWEL TYPE GUIDE

        **Horizontal Vowels (Y-axis):**  
        ㅏ, ㅑ, ㅓ, ㅕ, ㅐ, ㅒ, ㅔ, ㅖ, ㅣ

        **Vertical Vowels (Z-axis):**  
        ㅗ, ㅛ, ㅜ, ㅠ, ㅡ, ㅘ, ㅙ, ㅚ, ㅝ, ㅞ, ㅟ, ㅢ

        ---

        ### 🧮 SYLLABLE STRUCTURE (for grouping tools)
        Each syllable's jamo count (초성+중성(+종성)) is provided in order:

        {state["syllable_lengths"]}

        You MUST group the selected tools according to these counts and apply the correct Case (1~4) to each group.

        ---

        ### 🔎 CASE SELECTION TABLE
        | Length | Vowel Type   | Case  | Description                          |
        |--------|--------------|-------|--------------------------------------|
        | 2      | Horizontal   | Case 1 | 초성 + 중성 (Y-axis vowel)           |
        | 2      | Vertical     | Case 2 | 초성 + 중성 (Z-axis vowel)           |
        | 3      | Horizontal   | Case 3 | 초성 + 중성 + 종성 (Y-axis vowel)    |
        | 3      | Vertical     | Case 4 | 초성 + 중성 + 종성 (Z-axis vowel)    |

        ---

        ### 🧱 COORDINATE VALUES PER CASE

        **Case 1:** 초성 + 중성 (horizontal vowel)
        - 초성: [0.0, -0.05, 0.0]  
        - 중성: [0.0, 0.05, 0.0]

        **Case 2:** 초성 + 중성 (vertical vowel)
        - 초성: [0.0, 0.0, 0.05]  
        - 중성: [0.0, 0.0, -0.05]

        **Case 3:** 초성 + 중성 + 종성 (horizontal vowel)
        - 초성: [0.0, -0.03, 0.05]  
        - 중성: [0.0, 0.03, 0.05]  
        - 종성: [0.0, 0.0, -0.05]

        **Case 4:** 초성 + 중성 + 종성 (vertical vowel)
        - 초성: [0.0, 0.0, 0.05]  
        - 중성: [0.0, 0.0, 0.0]  ← ❗ MUST be zero offset!  
        - 종성: [0.0, 0.0, -0.1]

        ---

        ### ✅ OUTPUT FORMAT

        Only return valid JSON in this format:

        {{{{  
        "ㅂ_1": {{{{  
            "start": [0.0, 0.0, 0.05],  
            "end": [0.0, 0.0, 0.05]  
        }}}},  
        "ㅜ_2": {{{{  
            "start": [0.0, 0.0, 0.0],  
            "end": [0.0, 0.0, 0.0]  
        }}}},  
        "ㄱ_3": {{{{  
            "start": [0.0, 0.0, -0.1],  
            "end": [0.0, 0.0, -0.1]  
        }}}}  
        }}}}


        ❌ DO NOT include explanations or reasoning.
        ❌ DO NOT use markdown or wrap in ```json.
        ✅ Output MUST start with '{{' and end with '}}'.

        ---
        ⚠️ IMPORTANT:
        You MUST select Case 2 if the group has 2 jamo and the vowel is one of:
        ㅗ, ㅛ, ㅜ, ㅠ, ㅡ, ㅘ, ㅙ, ㅚ, ㅝ, ㅞ, ㅟ, ㅢ

        For example:
        - ㄹ + ㅗ → Case 2
        - ㅍ + ㅡ → Case 2

        DO NOT use Case 1 for vertical vowels. Absolutely never.
        ### 🚫 FINAL REMINDERS
        - Do NOT analyze or decompose the original text.
        - You MUST use ONLY the tools provided in the list, in exact order.
        - Do not guess or infer 초성/중성/종성 — follow syllable grouping.
        - Follow the Case rules strictly using the syllable structure and vowel type.
        """

        response = self.llm.invoke([
            SystemMessage(content="You are a Hangul character positioning assistant."),
            HumanMessage(content=prompt)
        ])

        raw = response.content.strip()
        with open("raw_llm_response.json", "w", encoding="utf-8") as f:
            f.write(raw)

        # Try to extract only the JSON part (fallback-safe)
        match = re.search(r"\{[\s\S]+\}", raw)
        cleaned = match.group(0) if match else raw

        try:
            adjusted_coordinates = json.loads(cleaned)
            state["adjusted_coordinates"] = adjusted_coordinates
            state["result"] = "Coordinates adjusted"
        except json.JSONDecodeError as e:
            st.write("❌ JSON decoding failed:", str(e))
            st.write("🔎 Raw output was:", raw)
            st.write("🔎 Cleaned JSON fragment:", cleaned)
            state["adjusted_coordinates"] = {}
            state["result"] = "Failed to parse JSON"

        return state



# Node: Create Tools
def create_tools(state):
    """Load available tools from the new JSON format and add them to state."""
    try:
        with open("modified_test.json", "r", encoding="utf-8") as file:
            tools_data = json.load(file)
    except Exception as e:
        st.write("[ERROR] Failed to load koreans.json:", str(e))
        state["available_tools"] = []
        return state

    if not isinstance(tools_data, dict) or "characters" not in tools_data:
        st.write("[ERROR] Unexpected format for tools JSON")
        state["available_tools"] = []
        return state

    characters = tools_data["characters"]
    available_tools = []

    for char in characters:
        if "name" in char and "path" in char:
            tool_entry = {
                "title": char["name"],               # Character name (e.g. ㄱ)
                "path": char["path"],                # Full path with start/end coordinates
                "y": -0.05,                          # Optional default y-offset
                "kind": char.get("kind", "unknown")  # Tool kind (e.g. 'son')
            }
            available_tools.append(tool_entry)

    state["available_tools"] = available_tools
    st.write("[DEBUG] Available Tools Loaded into State:", [tool["title"] for tool in available_tools])
    return state

# Node: Decompose Text
def decompose_text(state):
    """Decompose Hangul syllables into individual jamo characters and count jamo per syllable."""
    syllables = list(state["text"])
    decomposed = []
    syllable_lengths = []

    for syllable in syllables:
        jamos = list(j2hcj(h2j(syllable)))
        decomposed.extend(jamos)
        syllable_lengths.append(len(jamos)) 

    state["decomposed_text"] = decomposed
    state["syllable_lengths"] = syllable_lengths
    st.write("[DEBUG] Decomposed Text:", decomposed)
    st.write("[DEBUG] Syllable Lengths:", syllable_lengths)
    return state


# Node: Select Tools
def select_tools(state: Dict[str, any]) -> Dict[str, any]:
    """Select the necessary tools by mapping decomposed text to available tools.
    
    This node uses the existing SelectToolAgent to preserve maintainability.
    However, after obtaining the LLM output, it filters the tools based on the decomposed text,
    ensuring that only tools corresponding to the decomposed characters are selected.
    """
    if "decomposed_text" not in state:
        raise KeyError("[ERROR] 'decomposed_text' is missing from state!")
    if "available_tools" not in state:
        st.write("[ERROR] 'available_tools' is missing from state!")
        state["selected_tools"] = []
        return state

    available_tools = state.get("available_tools", [])
    if not available_tools:
        st.write("[ERROR] 'available_tools' is empty!")
        state["selected_tools"] = []
        return state

    agent = SelectToolAgent(available_tools)
    try:
        raw_selected = agent.run(state["decomposed_text"])
    except Exception as e:
        st.write("[ERROR] LLM Call Failed:", str(e))
        state["selected_tools"] = []
        return state
    tool_dict = {tool["title"]: tool for tool in available_tools}
    selected_tools = [tool_dict[char] for char in state["decomposed_text"] if char in tool_dict]

    st.write("Selected Tools:", [tool["title"] for tool in selected_tools])
    state["selected_tools"] = selected_tools
    return state    

def modify_coordinates(state: Dict[str, any]) -> Dict[str, any]:
    """
    Use ModifyCoordinatesAgent to adjust coordinates and output the result.
    
    This function instantiates the ModifyCoordinatesAgent and calls its run method,
    preserving the agent structure for maintainability. After the coordinates are adjusted,
    it outputs the adjusted coordinates using st.write.
    
    Args:
        state (Dict[str, any]): The current state containing text and selected_tools.
        
    Returns:
        Dict[str, any]: Updated state with adjusted_coordinates.
    """
    agent = ModifyCoordinatesAgent()
    updated_state = agent.run(state)
    if "adjusted_coordinates" in updated_state:
        st.write("Modified Coordinates:", updated_state["adjusted_coordinates"])
    else:
        st.write("Modified Coordinates not found.")
    return updated_state

def apply_global_y_offset(state: Dict[str, any]) -> Dict[str, any]:
    adjusted = state.get("adjusted_coordinates", {})
    text = state.get("text", "")
    offset_per_char = 0.15

    syllables = list(text)
    jamo_index = 0
    updated = {}

    for idx, syllable in enumerate(syllables):
        y_offset = idx * offset_per_char -0.3
        components = list(j2hcj(h2j(syllable)))
        for _ in components:
            key = list(adjusted.keys())[jamo_index]
            coord = adjusted[key]

            new_start = [round(coord["start"][i] + (y_offset if i == 1 else 0.0), 2) for i in range(3)]
            new_end = [round(coord["end"][i] + (y_offset if i == 1 else 0.0), 2) for i in range(3)]

            updated[key] = {
                "start": new_start,
                "end": new_end
            }
            jamo_index += 1

    state["adjusted_coordinates"] = updated
    st.write("✅ Y-axis offset applied (rounded):", updated)
    return state

# Node: Generate Code
def generate_code(state: Dict[str, any]) -> Dict[str, any]:
    """Generate full tool format with offset-applied path coordinates."""
    generated_tools_with_offsets = []

    def ensure_list(vec):
        """Fix dict-style vectors like {'0': 0.1, '1': 0.2, '2': 0.3} into list."""
        if isinstance(vec, dict) and all(k in ['0', '1', '2'] for k in vec.keys()):
            return [vec['0'], vec['1'], vec['2']]
        return vec

    adjusted_coords = state.get("adjusted_coordinates", {})
    selected_tools = state.get("selected_tools", [])

    for i, tool in enumerate(selected_tools):
        title = tool["title"]
        original_paths = tool.get("path", [])

        key = f"{title}_{i+1}"
        offset_entry = adjusted_coords.get(key, {"start": [0.0, 0.0, 0.0]})
        offset_vec = ensure_list(offset_entry.get("start", [0.0, 0.0, 0.0]))

        modified_path = []
        for stroke in original_paths:
            start = ensure_list(stroke["start"])
            end = ensure_list(stroke["end"])

            new_start = [round(float(start[j] + offset_vec[j]), 2) for j in range(3)]
            new_end = [round(float(end[j] + offset_vec[j]), 2) for j in range(3)]

            modified_path.append({
                "start": new_start,
                "end": new_end
            })

        # Reconstruct the tool with modified path
        modified_tool = {
            "name": title,
            "kind": tool.get("kind", "unknown"),
            "path": modified_path
        }

        generated_tools_with_offsets.append(modified_tool)

    # Store in state
    state["generated_tools_with_offsets"] = generated_tools_with_offsets
    state["result"] = "Final tool path generated"

    # Show result
    st.write("### Final Tool Paths with Offset Applied:")
    st.code(json.dumps(generated_tools_with_offsets, indent=2, ensure_ascii=False), language="json")

    # ✅ Save to file
    output = {"characters": generated_tools_with_offsets}
    with open("final_tool_paths.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return state

# Define the LangGraph Workflow
workflow = StateGraph(RobotState)
workflow.add_node("create_tools", create_tools)
workflow.add_node("decompose_text", decompose_text)
workflow.add_node("select_tools", select_tools)
workflow.add_node("modify_coordinates", modify_coordinates)
workflow.add_node("apply_y_offset", apply_global_y_offset)
workflow.add_node("generate_code", generate_code)
# workflow.add_node("execute_code", execute_code)

workflow.add_edge("create_tools", "decompose_text")
workflow.add_edge("decompose_text", "select_tools")
workflow.add_edge("select_tools", "modify_coordinates")
workflow.add_edge("modify_coordinates", "apply_y_offset")
workflow.add_edge("apply_y_offset", "generate_code")
# workflow.add_edge("generate_code", "execute_code")

# Set the entry point to the create_tools node
workflow.set_entry_point("create_tools")
graph = workflow.compile()

# Streamlit UI
st.title("Franka Robot Wall Writing")
user_input = st.text_input("Enter a character:")
if st.button("Generate and Execute"):
    result = graph.invoke({"text": user_input})
    st.write("Execution Completed.")
    if "result" in result:
        st.write("MoveIt Execution Result:", result["result"])