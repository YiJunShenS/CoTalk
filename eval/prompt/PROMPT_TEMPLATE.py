Prompt_Speech_Normalization = """You are a speech normalization tool. The following is the result of speech-to-text conversion. Please normalize the text. 
        Only keep the normalized text, do not modify fine-grained details, just remove noise caused by speech.
        Input text: {pre_text}
        Strictly follow the output format below:
        Output example:
        ```json
        {{"caption": "This is a car"}}
        ```
    """

Prompt_Text_Integration = """ You are a text integration expert. caption1 is the original annotation result, caption2 is the annotator's supplement.

Notes:
1. caption2 may correct or add missing details to caption1.
2. Merge identical semantic parts, avoid duplication.
3. Insert new content in the appropriate place.
4. In case of conflict, caption2 prevails.

Input:
caption1: {caption1}
caption2: {caption2}
Strictly follow this output format:
```json
{{"caption": "There are 5 airplanes parked in the airport..."}}
```
"""

Prompt_Is_Complete = """ You are asked to judge whether the image has been fully annotated. Input is one caption. 
If the caption means 'I think that's all', 'I think it's complete', etc., then output 0.

Input:
    caption: {caption}

Output:
```json
{{"caption": "0"}}
```

"""

Prompt_Caption_Refinement = """Please help me improve the following caption according to the steps below.
        Special attention:
        1. Correct obvious typos.
        2. Remove meaningless connecting words such as "then," "and," "furthermore," and "next."
        3. Output in English.
        4. Format the output according to the sample provided.
        Input caption:{caption}
        Output example:
        ```json{{
            "caption":"this is a image of the tiger."
        }}
        ```
"""

Prompt_Semantic_Unit_Parsing = """
    Please help me extract and segment the minimum semantic unit based on the following rules and reference the output examples.
    1.Unit Definition: Minimum semantic unit = object name + associated attributes; A single sentence may contain multiple independent units; Each unit must contain only one object name
    2.Attribute Specifications: Valid attributes: absolute_location (position in the overall image), relative_location(Position relative to other objects), colour, amount (Explicitly extract indefinite articles ("a"/"an") as standalone attributes. Include numerical values (e.g., "two", "three") and quantifiers (e.g., "some", "several")), size, shape, material, object_description, other(All other unclassified attributes are 'other', If there are multiple, please separate them with commas),Omit any attributes that do not exist; Prohibit attribute overlap or duplication; Pronoun-based locations (e.g., "this", "that") must be replaced with specific referenced objects
    3.Extraction Principles: Prioritize extracting the "name" field separately; Create independent units for multiple objects sharing attributes; Absolute and relative locations cannot coexist in the same unit; Omit unspecified/ambiguous attributes
    4.Output Requirements: Present only final results without reasoning processes

    Input text:{caption}

    Input Example 1: "This is a satellite remote sensing image of a tennis court area, with ten blue tennis courts in the middle and a green background, arranged in rows of five. There are parking areas in the lower left and lower right of the tennis court, where scattered cars are parked. In the upper left corner of the picture, there is a dense forest."
        Output Example 1:
        ```json
        [
            {{
                "name": "image",
                "attributes":{{
                    "amount": "a",
                    "object_description": "satellite remote sensing",
                    "other": [" of a tennis court area"]
                }}
            }},
            {{
                "name": "tennis court",
                "attributes":{{
                    "amount": "10",
                    "colour": "blue",
                    "shape": "arranged in rows of five",
                    "absolute_location": "at the center of picture",
                    "size": "large",
                    "material": "plastic",
                    "other": ["a green background"]
                }}
            }},
            {{
                "name": "parking areas",
                "attributes": {{
                    "relative_location":"in the lower left and lower right of the tennis court",
                    "object_description": "where scattered cars are parked"
                }}
            }},
            {{
                "name": "forest",
                "attributes": {{
                    "object_description": "dense",
                    "amount": "a",
                    "absolute_location": "In the upper left corner of the picture"
                }}
            }}
        ]
        Input Example 2: "This is a satellite remote sensing image showing a bridge passing diagonally from the upper right to the lower left corner. The sea surface appears green, with a patch of green seaweed visible under the bridge in the upper right area. Green trees and vast grasslands are on the small island in the upper left corner of the picture. On the bridge deck, white and black cars are driving, and a red bridge corridor is visible near the lower left of the image center. The bottom left corner of the image shows curved roads on land."
        Output Example 2:
        ```json
        [
            {{
                "name": "image",
                "attributes": {{
                    "amount": "a",
                    "object_description": "satellite remote sensing",
                    "other": ["showing a bridge"]
                }}
            }},
            {{
                "name": "bridge",
                "attributes": {{
                    "amount": "a"
                    "absolute_location": "passing diagonally from the upper right to the lower left corner"
                }}
            }},
            {{
                "name": "sea surface",
                "attributes": {{
                    "colour": "green",
                    "relative_location": "under the bridge in the upper right area"
                }}
            }},
            {{
                "name": "seaweed",
                "attributes": {{
                    "amount": "a patch of",
                    "colour": "green",
                    "relative_location": "under the bridge in the upper right area",
                    "other": ["visible"]
                }}
            }},
            {{
                "name": "trees",
                "attributes": {{
                    "colour": "green",
                    "absolute_location": "in the upper left corner of the picture",
                    "object_description": "on the small island"
                }}
            }},
            {{
                "name": "grasslands",
                "attributes": {{
                    "size": "vast",
                    "absolute_location": "in the upper left corner of the picture",
                    "object_description": "on the small island"
                }}
            }},
            {{
                "name": "island",
                "attributes": {{
                    "size": "small",
                    "absolute_location": "in the upper left corner of the picture"
                }}
            }}
            {{
                "name": "car",
                "attributes": {{
                    "colour": "white",
                    "relative_location": "on the bridge deck",
                    "other": ["are driving"]
                }}
            }},
            {{
                "name": "car",
                "attributes": {{
                    "colour": "black",
                    "relative_location": "on the bridge deck",
                    "other": ["are driving"]
                }}
            }},
            {{
                "name": "bridge corridor",
                "attributes": {{
                    "amount": "a",
                    "colour": "red",
                    "relative_location": "near the lower left of the image center",
                    "other": ["visible"]
                }}
            }},
            {{
                "name": "roads",
                "attributes": {{
                    "shape": "curved",
                    "absolute_location": "in the bottom left corner of the image",
                    "relative_location": "on land"
                }}
            }}
        ]
        ```  
        Input Example 3: "This is an image of a parking lot area. In the middle of the image is a parking lot area with a white solid line, where many large white trucks are parked. There are three gray cars and two white cars parked at the bottom right of the rectangular building. There are small parking areas on the left and above of the building, with two black cars parked on the left and five cars parked in the upper parking area, which are white, red, and black. "
        Output Example 3:
        ```json
        [
            {{
                "name": "image",
                "attributes": {{
                    "amount": "an",
                    "object_description": "of a parking lot area"
                }}
            }},
            {{
                "name": "parking lot",
                "attributes": {{
                    "amount": "a",
                    "absolute_location": "in the middle of the image",
                    "object_description": "with a white solid line",
                    "other": ["many large white trucks parked"]
                }}
            }},
            {{
                "name": " solid line",
                "attributes":{{
                    "amount": "a",
                    "colour": "white",
                    "relative_location": "in the parking lot"
                }}
            }},
            {{
                "name": "truck",
                "attributes": {{
                    "amount": "many",
                    "colour": "white",
                    "size": "large",
                    "relative_location": "in the parking lot",
                    "other": ["parked"]
                }}
            }},
            {{
                "name": "car",
                "attributes": {{
                    "amount": "three",
                    "colour": "gray",
                    "relative_location": "at the bottom right of the rectangular building",
                    "other": ["parked"]
                }}
            }},
            {{
                "name": "car",
                "attributes": {{
                    "amount": "two",
                    "colour": "white",
                    "relative_location": "at the bottom right of the rectangular building",
                    "other": ["parked"]
                }}
            }},
            {{
                "name": "building",
                "attributes": {{
                    "shape": "rectangular"
                }}
            }},
            {{
                "name": "parking area",
                "attributes": {{
                    "size": "small",
                    "relative_location": "on the left and above of the building",
                    "other": ["for parking"]
                }}
            }},
            {{
                "name": "car",
                "attributes": {{
                    "amount": "two",
                    "colour": "black",
                    "relative_location": "on the left parking area",
                    "other": ["parked"]
                }}
            }},
            {{
                "name": "car",
                "attributes": {{
                    "amount": "five",
                    "colour": "white, red, and black",
                    "relative_location": "in the upper parking area",
                    "other": ["parked"]
                }}
            }}
        ]
        ```
        Input Example 4: "This is a remote sensing satellite image of a port and coastline. On the left side of the image, half of the area is an island, with green forests and grasslands distributed on the island, and there are some houses on the grassland. "
        Output Example 4:
        ```json
        [
            {{
                "name": "image",
                "attributes": {{
                    "amount": "a",
                    "object_description": "remote sensing satellite",
                    "other": ["of a port and coastline"]
                }}
            }},
            {{
                "name": "island",
                "attributes": {{
                    “amount”: “an”,
                    "absolute_location": "on the left side of the picture",
                    "size": "half of the area",
                    "object_description": "with green forests and grasslands"
                }}
            }},
            {{
                "name": "forest",
                "attributes": {{
                    "colour": "green",
                    "relative_location": "on the island",
                    "other": [distributed]
                }}
            }},
            {{
                "name": "grasslands",
                "attributes": {{
                    "colour": "green",
                    "relative_location": "on the island",
                    "other": [distributed]
                }}
            }},
            {{
                "name": "house",
                "attributes": {{
                    "amount": "some",
                    "relative_location": "on the grassland"
                }}
            }} 
        ]
        ```
        Input Example 5: "This is a satellite remote sensing image of a sports venue. There are some green trees planted around the sports field. The center of the picture is a large playground with a red plastic track and a green lawn rugby field. Above the playground are four tennis courts and a gray hexagonal gray building. Above the tennis court is a building with a white roof. The upper left, upper right, and lower right corners of the picture are all parking lots, where white, red, and black cars are parked. The bottom left corner of the picture is a road."
        Output Example 5:
        ```json
        [
            {{
                "name": "image",
                "attributes": {{
                    "amount": "a",
                    "object_description": "satellite remote sensing",
                    "other": ["of a sports venue"]
                }}
            }},
            {{
                "name": "tree",
                "attributes": {{
                    "colour": "green",
                    "relative_location": "around the sports field",
                    "other": ["planted"]
                }}
            }},
            {{
                "name": "playground",
                "attributes": {{
                    "amount": "a",
                    "size": "large",
                    "absolute_location": "the center of the picture",
                    "other": ["with a red plastic track and a green lawn rugby field"]
                }}
            }},
            {{
                "name": "track",
                "attributes": {{
                    "amount": "a",
                    "colour": "red",
                    "material": "plastic",
                    "relative_location": "on the playground"
                }}
            }},
            {{
                "name": "rugby field",
                "attributes": {{
                    "amount": "a",
                    "colour": "green",
                    "material": "lawn",
                    "relative_location": "on the playground"
                }}
            }},
            {{
                "name": "tennis court",
                "attributes": {{
                    "amount": "four",
                    "absolute_location": "above the playground"
                }}
            }},
            {{
                "name": "building",
                "attributes": {{
                    "colour": "gray",
                    "shape": "hexagonal",
                    “relative_location": "above the playground"
                }}
            }},
            {{
                "name": "building",
                "attributes": {{
                    "amount": "a",
                    "object_description": “with a white roof",
                    " relative _location": "above the tennis court"
                }}
            }},
            {{
                "name": "parking lot",
                "attributes": {{
                    "amount": "a",
                    "absolute_location": "upper left corner of the picture",
                    "other": [" where white, red, and black cars are parked "]
                }}
            }},
            {{
                "name": "car",
                "attributes": {{
                    "colour": "white, red, and black ",
                    "absolute_location": " The upper left, upper right, and lower right corners of the picture ",
                    "other": ["in the parking lot"]
                }}
            }},
            {{
                "name": "parking lot",
                "attributes": {{
                    "amount": "a",
                    "absolute_location": "upper right corner of the picture",
                    "other": [" where white, red, and black cars are parked "]
                }}
            }},
            {{
                "name": "parking lot",
                "attributes": {{
                    "amount": "a",
                    "absolute_location": "lower right corner of the picture",
                    "other": [" where white, red, and black cars are parked "]
                }}
            }},
            {{
                "name": "road",
                "attributes": {{
                    "amount": "a",
                    "absolute_location": "bottom left corner of the picture"
                }}
            }}
        ]
        ```

    """ 