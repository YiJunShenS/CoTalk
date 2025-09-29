import os
import json
import argparse

def main(image_folder, json_folder):
    if not os.path.exists(json_folder):
        os.makedirs(json_folder)

    # Load the image names from the directory specified in arguments
    image_names = os.listdir(image_folder)

    # Define JSON template for image annotation metadata
    json_template = {
        "image_name": "",  # Placeholder for the name of the image file.
        "image_status": "unlocked",  # Status indicating if the image is locked for annotation.
        "annotation_completed": "No",  # Indicates if annotation for this image is completed.
        "lock_time": "",  # Time when the image was locked for annotation.
        "overall_annotation": "",  # Overall annotation for the image.
        "overall_annotation_history": [],  # History of overall annotations.
        "annotation_history": []  # Annotation history for the image.
    }

    # Iterate over each image name and create corresponding JSON file
    for image_name in image_names:
        # Skip files that are not images (if necessary)
        if not image_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            continue

        # Create JSON file name based on image file name
        json_file_name = os.path.splitext(image_name)[0] + ".json"
        json_file_path = os.path.join(json_folder, json_file_name)

        # Update the "image_name" field in the JSON template
        json_template["image_name"] = image_name

        # Skip creation of JSON file if it already exists
        if os.path.exists(json_file_path):
            continue

        # Write the template to a JSON file
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(json_template, json_file, ensure_ascii=False, indent=4)
        
        print(f"Created: {json_file_name}")

    print("All JSON files have been initialized.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate JSON files for images in a specified folder.")
    parser.add_argument('--image_folder', type=str, default= "data/image", help='The folder containing images.')
    parser.add_argument('--save_json_folder', type=str, default= "output/annotation_json", help='The folder to save JSON files.')

    args = parser.parse_args()
    
    main(args.image_folder, args.save_json_folder)