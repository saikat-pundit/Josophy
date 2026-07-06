import os, sys, datetime
from openai import OpenAI

def transmit_payload_to_ai():
    # Find the latest FO Analysis file
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        print("❌ No reports directory found. Run data_processing.py first.")
        sys.exit(1)
    
    # Get all FO Analysis files
    analysis_files = [f for f in os.listdir(reports_dir) if f.startswith("FO Analysis_") and f.endswith(".txt")]
    if not analysis_files:
        print("❌ No FO Analysis files found. Run data_processing.py first.")
        sys.exit(1)
    
    # Get the latest file
    latest_file = max(analysis_files)
    prompt_file_path = os.path.join(reports_dir, latest_file)
    date_str = latest_file.replace("FO Analysis_", "").replace(".txt", "")
    
    # Check if AI report already exists
    ai_report_path = f"reports/ai_market_analysis_{date_str}.txt"
    if os.path.exists(ai_report_path):
        print(f"✅ AI analysis already exists for date {date_str}. Skipping.")
        return
    
    with open(prompt_file_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    if not NVIDIA_API_KEY:
        print("⚠️ No NVIDIA_API_KEY found. Ensure it is set in your environment variables.")
        return

    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=NVIDIA_API_KEY)

    print(f"🔄 Requesting analysis from deepseek-v4-pro for {date_str}...\n")
    print("======================================================================")
    
    try:
        completion = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-pro",
            messages=[{"role": "system", "content": "You are an elite institutional market strategist specialized in the Indian National Stock Exchange (NSE) derivatives data analysis."},
                     {"role": "user", "content": prompt}],
            temperature=0.8, top_p=0.95, max_tokens=30000,
            extra_body={"chat_template_kwargs": {"thinking": True}}, stream=True
        )

        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
        
        print("\n======================================================================")
        print("✅ Stream complete.")

        with open(ai_report_path, "w", encoding="utf-8") as f:
            f.write(full_response)
        print(f"💾 Analysis saved to: {ai_report_path}")
        
    except Exception as err:
        print(f"\n❌ Error during API communication: {err}")

if __name__ == "__main__":
    transmit_payload_to_ai()
