Pixelfed Image Publisher
This script allows you to automatically publish images to any Pixelfed instance without manual intervention.

How it works
Publishing parameters are read from a dedicated file named queue.csv.
Each line in the file may contain:

image path (required)

image name

post text

alt‑text

NSFW flag

content warning text

If the alt‑text field is empty, the script will generate it automatically. On some systems this operation may be slow or inconvenient.

Queue processing
After a post is successfully published:

the corresponding line is removed from queue.csv

the original image is archived inside a subdirectory located under the bot’s main directory
