import os
from datetime import datetime
from openai import OpenAI

# Import our new data processing module
from data_processing+prompt import prepare_prompt_and_context

def main():
    print("🚀 Starting parallel DeepSeek-v4-Pro yield report...")
    
    # 1. Fetch the pre-calculated prompt and file destinations
    # Passing "deepseek" ensures the output file is named deepseek_report_YYYY-MM-DD.txt
    prompt, date_str, report_file = prepare_prompt_and_context(ai_name="deepseek")
    
    if not prompt:
        print("⚠️ Failed to generate prompt. Exiting.")
        return

    # 2. Setup API Client
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    if not NVIDIA_API_KEY:
        print("⚠️ No NVIDIA_API_KEY found. Check GitHub Secrets.")
        return

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY
    )

    print(f"🔄 Requesting analysis from deepseek-v4-pro (Streaming) for {date_str}...")

    try:
        # 3. Call the AI Model
        completion = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-pro",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            top_p=0.95,
            max_tokens=30000,
            extra_body={"chat_template_kwargs": {"thinking": True}},
            stream=True
        )
        
        analysis_content = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                analysis_content += chunk.choices[0].delta.content

        print("✅ Analysis generated successfully. Saving report...")

        # 4. Format and Save the Report
        report = f"============================================================\n"
        report += f"📅 YIELD CURVE DAILY REPORT (DEEPSEEK PRO) - {date_str}\n"
        report += f"============================================================\n\n"
        report += f"📋 AI ANALYSIS:\n{analysis_content}\n"
        report += f"============================================================\n"
        report += f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | NVIDIA DeepSeek-V4-Pro\n"
        
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"📄 DeepSeek report saved to: {report_file}")

    except Exception as e:
        print(f"\n⚠️ NVIDIA DeepSeek API error: {e}")

if __name__ == "__main__":
    main()
