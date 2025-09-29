import gradio as gr
import whisper
import os
import argparse
from datetime import datetime
import shutil
import json
import re
from pathlib import Path
import random
from llm.llm import llm
from prompt.PROMPT_TEMPLATE import Prompt_Speech_Normalization, Prompt_Text_Integration, Prompt_Is_Complete

import threading
from schedule_unlock import start_unlocker_job

def parse_args():
    parser = argparse.ArgumentParser(description="Chain-of-Talkers (CoTalk): Fast Human Annotation of Dense Image Captions")

    # Model settings
    parser.add_argument("--model_size", type=str, default="large", help="Whisper model size (tiny, base, small, medium, large)")
    parser.add_argument("--model_download_root", type=str, default="envs/whisper", help="Whisper model download path")

    # Data paths
    parser.add_argument("--json_folder_path", type=str, default="output/annotation_json", help="save JSON folder path")
    parser.add_argument("--original_image_folder", type=str, default="data/image", help="Original image folder path")
    parser.add_argument("--audio_save_dir", type=str, default="output/audio", help="Audio save directory")

    # Server settings
    parser.add_argument("--server_name", type=str, default="", help="Server IP or domain name")
    parser.add_argument("--server_port", type=int, default=7860, help="Server port")
    parser.add_argument("--share", action="store_true", help="Whether to generate a public share link")
    parser.add_argument("--ssl_certfile", type=str, default="cert.pem", help="SSL certificate file path")
    parser.add_argument("--ssl_keyfile", type=str, default="key.pem", help="SSL private key file path")
    parser.add_argument("--ssl_verify", action="store_true", help="Verify SSL (default False)")

    # annotation num
    parser.add_argument("--person_num", type=int, default=2, help="If > 0, specifies the exact number of annotations required for completion. "
             "If <= 0, indicates that annotation can only be completed when someone explicitly states there are no further additions needed.")

    # schedule settings
    parser.add_argument("--interval_seconds", type=int, default=10, help="Interval in seconds between checks (default: 10)")
    parser.add_argument("--timeout_minutes", type=int, default=15, help="Lock timeout duration in minutes. Files locked longer than this will be unlocked (default: 15)")
    
    return parser.parse_args()


# Global variables (initialized by args)
args = parse_args()

# Load Whisper model
model = whisper.load_model(args.model_size, download_root=args.model_download_root)

# Create audio save directory
os.makedirs(args.audio_save_dir, exist_ok=True)


# Extract JSON content
def process_json(json_str):
    json_block_pattern = r'```json(.*?)```'
    match = re.search(json_block_pattern, json_str, re.DOTALL)
    try:
        json_str = match.group(1).strip()
    except:
        json_str = json_str.strip()
    json_data = json.loads(json_str)
    if 'caption' in json_data:
        return json_data['caption']
    else:
        return json_data

# Speech-to-text normalization
def process(pre_text):
    prompt_normalization = Prompt_Speech_Normalization.format(
        pre_text=pre_text,
    )
    llm_result = llm(prompt_normalization)
    # print("LLM normalization output:", llm_result)
    return process_json(llm_result)


# Merge historical annotations
def process_history_annotation(caption1, caption2):
    prompt = Prompt_Text_Integration.format( 
        caption1= caption1,
        caption2 = caption2
    )
    llm_result = llm(prompt)
    print("Merged historical annotation:", llm_result)
    return process_json(llm_result)


# Judge if annotation is complete
def judged_all_annotations(caption):
    prompt = Prompt_Is_Complete.format(
        caption= caption,
    )
    llm_result = llm(prompt)
    is_complete = process_json(llm_result)
    if is_complete == '0':
        return True
    else:
        return False


# Find an unlocked image
def find_unlocked_image(checksum):
    json_files = [f for f in os.listdir(args.json_folder_path) if f.endswith('.json')]
    random.shuffle(json_files)

    for json_filename in json_files:
        json_filepath = os.path.join(args.json_folder_path, json_filename)
        try:
            with open(json_filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)

            if data.get("image_status") == "unlocked" and data.get("annotation_completed") == 'No':
                history = data.get('annotation_history', [])
                # check whether the image is completed or whether the same person has annotated
                ids = [item['id'] for item in history if 'id' in item]
                if checksum not in ids:
                    print(f"Selected image: {json_filename}")

                    # Lock the image
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    data['lock_time'] = current_time
                    data['image_status'] = 'locked'

                    with open(json_filepath, 'w', encoding='utf-8') as file:
                        json.dump(data, file, ensure_ascii=False, indent=4)

                    image_name = data["image_name"]
                    image_path = os.path.join(args.original_image_folder, image_name)
                    all_label = data.get("overall_annotation", "")

                    return {
                        "image": image_path,
                        "json_path": json_filepath,
                        "overall_annotation": all_label
                    }
        except Exception as e:
            print(f"Failed to read {json_filename}: {e}")
            continue

    return {"image": None}

# Speech recognition
def transcribe_audio(audio_path, json_path_textbox):
    if not audio_path:
        return ""
    
    # Save audio file
    filename_without_ext = os.path.splitext(os.path.basename(json_path_textbox))[0]
    current_audio_save = os.path.join(args.audio_save_dir, filename_without_ext)
    os.makedirs(current_audio_save, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(current_audio_save, f"audio_{timestamp}.wav")
    shutil.copy2(audio_path, save_path)

    result = model.transcribe(save_path)
    text = result["text"]

    # Normalize text
    processed_text = process(text)
    print("Speech recognition result:", processed_text)
    return processed_text


# Submit annotation
def submit_annotation(new_annotation_input, original_image, json_path_textbox, history_label, input_help, checksum):
    if not new_annotation_input or not json_path_textbox:
        return [original_image, json_path_textbox, history_label, input_help, checksum, None, ""]

    with open(json_path_textbox, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Add historical annotation
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    original_label = {
        "id": len(data['annotation_history']) + 1,
        "annotation_info": {
            "annotator_id": checksum,
            "annotation": new_annotation_input,
            "start_time": data['lock_time'],
            "end_time": current_time
        }
    }
    data['annotation_history'].append(original_label)

    # Update overall annotation
    if not data.get("overall_annotation_history"):
        data['overall_annotation'] = new_annotation_input
        history_all_label = {
            "id": 1,
            "description": new_annotation_input,
            "start_time": data['lock_time'],
            "end_time": current_time
        }
        data['overall_annotation_history'] = [history_all_label]
    else:
        # first check whether the annoation is over
        if judged_all_annotations(new_annotation_input):
            data['annotation_completed'] = 'Yes'
        else:
            processed_label = process_history_annotation(data['overall_annotation'], new_annotation_input)
            data['overall_annotation'] = processed_label
            history_all_label = {
                "id": len(data['overall_annotation_history']) + 1,
                "description": processed_label,
                "start_time": data['lock_time'],
                "end_time": current_time
            }
            data['overall_annotation_history'].append(history_all_label)

    # Mark annotation as completed
    if args.person_num > 0 and len(data['annotation_history']) >= args.person_num:
        data['annotation_completed'] = 'Yes'

    # Write back to file
    with open(json_path_textbox, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    return update_view(json_path_textbox, checksum)


# Update view
def update_view(json_path_textbox, checksum):

    if json_path_textbox and os.path.exists(json_path_textbox):
        with open(json_path_textbox, 'r', encoding='utf-8') as file:
            data = json.load(file)
        if data.get('annotation_completed') == 'No':
            data['image_status'] = 'unlocked'
            data['lock_time'] = ""
            with open(json_path_textbox, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

    result = find_unlocked_image(checksum)
    if not result.get("overall_annotation"):
        return [
            result['image'],
            gr.update(value=result.get('json_path', ''), visible=False),
            "Please describe the image as thoroughly as possible",
            gr.update(value="### Please follow the sample format and describe the image in detail."),
            gr.update(value=checksum),
            gr.update(value=None),
            gr.update(value="")
        ]
    else:
        return [
            result['image'],
            gr.update(value=result.get('json_path', ''), visible=False),
            result["overall_annotation"],
            gr.update(value="### Please refer to the sample and point out what is missing or incorrect in the previous annotations. If you believe the annotation is already complete, simply enter 'none'."),
            gr.update(value=checksum),
            gr.update(value=None),
            gr.update(value="")
        ]


# First interface
def first_interface():
    with gr.Blocks() as first_ui:
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Image to be annotated")
                original_image = gr.Image(value="gradio_image//begin.jpg", label="Image")
                gr.Markdown("### Please click [Start Annotation] to begin the image annotation task")

            with gr.Column(elem_classes="center-button"):
                gr.Markdown("### Help image")
                help_image = gr.Image(value="gradio_image//begin.jpg", label="Help image")
                start_button = gr.Button("Start Annotation", variant="primary")
    return first_ui, start_button


# Second interface
def second_interface():
    result = find_unlocked_image("10086")
    img_path = result['image'] if result['image'] else "gradio_image//begin.jpg"
    json_path = result.get('json_path', '')

    initial_text = result.get("overall_annotation", "")
    if not initial_text:
        initial_text = "Please describe the image as thoroughly as possible"
        help_md = "### Please follow the sample format and describe the image in detail."
    else:
        help_md = "### Please refer to the sample and point out what is missing or incorrect in the previous annotations. If you believe the annotation is already complete, simply enter 'none'."

    with gr.Blocks(css=".large-font-textbox textarea { font-size: 20px !important; }") as second_ui:
        gr.Markdown("## Image Annotation Platform")

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Image to be annotated")
                original_image = gr.Image(value=img_path, label="Image", height=800, width=800)
                json_path_textbox = gr.Textbox(value=json_path, label="JSON path", visible=False)

            with gr.Column():
                input_help = gr.Markdown(help_md)
                gr.Markdown("### Historical annotation")
                history_label = gr.Textbox(value=initial_text, label="Latest annotation", lines=8, interactive=False)
                audio_input = gr.Microphone(type='filepath', label="Record voice")
                transcribe_btn = gr.Button("Transcribe Speech")
                new_annotation_input = gr.Textbox(label="New annotation text", lines=6)
                audio_save_path = gr.Textbox(label="Audio save path", visible=False)
                checksum = gr.Textbox(label="Verification code", value="1", visible=True)

                with gr.Row():
                    submit_btn = gr.Button("Submit Annotation", variant="primary")
                    refresh_btn = gr.Button("Refresh Image")

        transcribe_btn.click(
            fn=transcribe_audio,
            inputs=[audio_input, json_path_textbox],
            outputs=new_annotation_input
        )

        submit_btn.click(
            fn=submit_annotation,
            inputs=[new_annotation_input, original_image, json_path_textbox, history_label, input_help, checksum],
            outputs=[original_image, json_path_textbox, history_label, input_help, checksum, audio_input, new_annotation_input]
        )

        refresh_btn.click(
            fn=update_view,
            inputs=[json_path_textbox, checksum],
            outputs=[original_image, json_path_textbox, history_label, input_help, checksum]
        )

    return second_ui


# Main interface
with gr.Blocks() as demo:
    with gr.Tab("Annotation Example"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Example images")
                example_image1 = gr.Image(value="gradio_image//P0008.png", label="Example image 1", height=500, width=800)
                example_image2 = gr.Image(value="gradio_image//P0210.png", label="Example image 2", height=500, width=800)

            with gr.Column():
                gr.Markdown("### Annotation examples")
                example_label1 = gr.Textbox(
                    value="This satellite image shows a top-down view of a parking lot and the surrounding area. On the left side of the image is a row of neatly parked large trucks, mainly in white, red, and gray. Each truck has its own parking space, and the vehicles are arranged in an orderly manner. On the right side is a building area, where several houses with black or brown roofs are scattered. One of the houses has an antenna tower standing on its roof, with several windows and doors visible on its facade. The surrounding area includes patches of grass and a few trees, along with roads and paths leading in and out of the parking lot for vehicle access. The surface of the parking lot shows signs of wear, with noticeable cracks and patches.",
                    label="Annotation example 1", lines=15, elem_classes="large-font-textbox"
                )
                gr.Markdown("")
                example_label2 = gr.Textbox(
                    value="This image is a bird’s-eye view of an airport or airfield. The central feature of the image is a long, straight runway. The runway appears to be made of asphalt and has visible markings, including dashed lines and numbers indicating its length. Several small aircraft are parked on the runway. These planes are likely general aviation aircraft, such as Cessnas or similar light airplanes. They are lined up in a row, with some facing toward the camera and others facing away. Near the runway, there are taxiways and apron areas where additional planes can be parked. These areas are paved and have clear boundaries for parking and movement. On the right side of the image, there are several buildings, , which may be hangars, maintenance facilities, or administrative offices. The buildings are rectangular in shape with flat roofs. Next to the buildings is a parking lot filled with cars, suggesting that the facility is in operation and likely used by pilots and staff. Surrounding the paved areas, there is some vegetation, including grass and trees. In the upper right corner of the image, there are also many small cars parked — a total of 37, in colors such as red and white.",
                    label="Annotation example 2", lines=15, elem_classes="large-font-textbox"
                )

    with gr.Tab("Annotation Platform"):
        with gr.Column(visible=True) as col1:
            first_ui, start_button = first_interface()
        with gr.Column(visible=False) as col2:
            second_ui = second_interface()

        start_button.click(
            fn=lambda: [gr.update(visible=False), gr.update(visible=True)],
            inputs=None,
            outputs=[col1, col2]
        )


# Launch application
if __name__ == "__main__":
    unlocker_thread = threading.Thread(
        target=start_unlocker_job,
        kwargs={
            'interval_seconds': args.interval_seconds,
            'timeout_minutes': args.timeout_minutes,
            'folder_path': args.json_folder_path
        },
        daemon=True 
    )
    unlocker_thread.start()

    demo.launch(
        share=args.share,
        server_name=args.server_name,
        server_port=args.server_port,
    )
