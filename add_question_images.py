#!/usr/bin/env python3
import os
import sys
import django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from questionnaires.models import QuestionOption
from django.core.files import File

def add_images_to_options():
    """Add images to the two options for question 59"""
    
    # Get the options
    options = QuestionOption.objects.filter(question_id=59)
    if options.count() < 2:
        print("Error: Could not find 2 options for question 59")
        return
    
    opt1, opt2 = options[0], options[1]
    
    # Image paths - you can modify these
    question_options_dir = '/Users/annjan/Downloads/medical_platform/media/question_options'
    
    # Check for common image names
    possible_names = ['option1.jpg', 'option2.jpg', 'image1.jpg', 'image2.jpg', 
                      'opt1.jpg', 'opt2.jpg', 'choice1.jpg', 'choice2.jpg']
    
    images_found = []
    for name in possible_names:
        path = os.path.join(question_options_dir, name)
        if os.path.exists(path):
            images_found.append((name, path))
    
    print(f"Found {len(images_found)} images:")
    for name, path in images_found:
        print(f"  - {name}")
    
    if len(images_found) >= 2:
        # Assign first two images to the options
        img1_name, img1_path = images_found[0]
        img2_name, img2_path = images_found[1]
        
        print(f"\nAdding {img1_name} to Option 1...")
        with open(img1_path, 'rb') as f:
            opt1.option_image.save(img1_name, File(f))
        
        print(f"Adding {img2_name} to Option 2...")
        with open(img2_path, 'rb') as f:
            opt2.option_image.save(img2_name, File(f))
        
        print("\n✅ Images added successfully!")
        print("Refresh the questionnaire page to see the images.")
        
    else:
        print("\n❌ Could not find at least 2 images.")
        print("Please place your images in: /Users/annjan/Downloads/medical_platform/media/question_options/")
        print("Supported formats: .jpg, .jpeg, .png, .gif, .bmp")

if __name__ == "__main__":
    add_images_to_options()
