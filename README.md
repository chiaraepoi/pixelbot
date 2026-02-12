# Pixelfed Image Publisher Bot

This script allows you to independently publish images to any Pixelfed instance.

## How it works

Publishing parameters are read from a dedicated file named `queue.csv`.  
Each line may contain:

- image path **(required)**
- image name
- post text
- alt-text
- NSFW flag
- content warning text

If the alt-text field is missing, the script automatically generates one.  
On some systems this operation may be slow or inconvenient.

## Queue processing

After publishing is complete:

- the corresponding line is removed from `queue.csv`
- the original image is archived inside a subdirectory located under the bot’s main directory
