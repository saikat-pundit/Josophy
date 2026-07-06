import os
import sys
import datetime
from openai import OpenAI

def transmit_payload_to_ai():
    prompt_file_path = "reports/processed_data_prompt.txt"
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    report_output_path = f"reports/ai_market_analysis_{date_str}.txt"
    
    if not os.path.exists(prompt_file_path):
        print(f"Error: Prompt payload missing at '{prompt_file_path}'. Run data_processing.py first.")
        sys.exit(1)
        
    # Read the compiled AI system prompt/data file
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        prompt = f.read()
        
    # Setup API Client
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    if not NVIDIA_API_KEY:
        print("⚠️ No NVIDIA_API_KEY found. Ensure it is set in your environment variables or GitHub Secrets.")
        return

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY
    )

    print(f"🔄 Requesting analysis from deepseek-v4-pro (Streaming) for {date_str}...\n")
    print("======================================================================")
    
    try:
        # Call the AI Model
        completion = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-pro",
            messages=[
                {"role": "system", "content": "You are an elite institutional market strategist specialized in the Indian National Stock Exchange (NSE) derivatives data analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            top_p=0.95,
            max_tokens=30000,
            extra_body={"chat_template_kwargs": {"thinking": True}},
            stream=True
        )

        full_response = ""
        
        # Iterate through the stream and print in real-time
        for chunk in completion:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
                
        print("\n======================================================================")
        print("✅ Stream complete.")

        # Save the final response to a report file
        with open(report_output_path, "w", encoding="utf-8") as f:
            f.write(full_response)
        print(f"💾 Analysis saved successfully to: {report_output_path}")
        
    except Exception as err:
        print(f"\n❌ An error occurred during API communication: {err}")

if __name__ == "__main__":
    transmit_payload_to_ai()
