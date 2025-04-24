# CCV Generator
Helps import and generate CCVs (Canadian Common CV) by relying on an intermediary yaml format. The generated XML files can then be imported in the CCV website. In short, it helps you:
- Convert an XML CCV to a readable and editable yaml format
- Convert a yaml CCV to an XML CCV (so that it can be imported in the CCV website)
- Generate a new CCV from scratch using a yaml template

The code can also be used as an API to build CCV generators.

## Installation
```bash
pip install ccv-generator
```

## Usage (Command line)
```bash
ccv_generator -h
usage: ccv_generator [-h] [-i INPUT] [-f FILTER] [-q | --quiet | --no-quiet] output

Generate a CCV XML file from a YAML file. Or export a CCV XML file to a YAML file.

positional arguments:
  output                The output file. Can be either a CCV XML file or a YAML file.

options:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        The input file. Can be either a CCV XML file or a YAML file.
  -f FILTER, --filter FILTER
                        Filter to parse only a subset of the CCV XML file. Should be a path of the section(s) to parse (e.g., "Contributions/Publications/Conference Publications" to export
                        only Conference Publications)
  -q, --quiet, --no-quiet
                        Avoid adding comments to the generated yaml file (default: False)
```


### Examples
#### Convert a CCV XML file to a YAML file
```bash
ccv_generator -i ccv.xml ccv.yaml
```

#### Convert a YAML file to a CCV XML file
```bash
ccv_generator -i ccv.yaml ccv.xml
```

#### Generate a CCV yaml template
```bash
ccv_generator ccv.yaml
```
This will generate a CCV yaml file with the default structure. You can then edit the file and use it to generate a CCV XML file. You can also only generate a specific section of the CCV (e.g., only conference publications) by using the `-f` option:
```bash
ccv_generator -f "Contributions/Publications/Conference Publications" ccv.yaml
```

## Usage (API)
Two functions are exposed to read and generate CCV xml files from/to python dictionaries:

parse_xml_ccv, build_xml_ccv


- `parse_xml_ccv(tree_model, section_filter=[], add_comments=True) -> dict`: Reads an XML structure and returns a dictionary representation of the CCV.
- `build_xml_ccv(data) -> str`: Builds an XML structure from a dictionary representation of the CCV. The dictionary should be in the format expected by the CCV XML schema.

### Example

Converting a bibtex (.bib) to the publication section of the CCV that can be imported in the CCV website (requires pybtex):
```python
from pybtex.database.input import bibtex
from ccv_generator import build_xml_ccv
import xml.etree.ElementTree as ET

MY_NAME = "John Doe"

publications = {
    "Contributions": {
        "Publications": {
            "Journal Articles": [],
        }
    }
}
parser = bibtex.Parser()
bib_data = parser.parse_file('publications.bib')


def get_author(author):
    return " ".join(author.first_names) + " " + " ".join(author.last_names)

def location_to_country(location):
    location = location.split(",")[-1].strip()
    if location == "USA": location = "United States of America"
    return location


for entry in bib_data.entries:
    entry_data = bib_data.entries[entry]
    publication = {}

    author_position = 1

    if get_author(entry_data.persons["author"][0]) == MY_NAME:
        author_position = 0
    elif get_author(entry_data.persons["author"][-1]) == MY_NAME:
        author_position = -1


    publication["Contribution Role"] = "Co-Author"
    if author_position == 0:
        publication["Contribution Role"] = "First Listed Author"
    elif author_position == -1:
        publication["Contribution Role"] = "Last Listed Author"

    publication["Contribution Percentage"] = "81-90" if author_position == 0 else "31-40"
    publication["Number of Contributors"] = str(len(entry_data.persons["author"]))

    publication["Authors"] = "; ".join([str(author) for author in entry_data.persons["author"]])

    if "journal" in entry_data.fields:
        publication["Article Title"] = entry_data.fields["title"]
        publication["Journal"] = entry_data.fields["journal"]
        publication["Volume"] = entry_data.fields["volume"]
        #publication["Issue"] = 
        publication["Page Range"] = entry_data.fields["pages"] if "pages" in entry_data.fields else "1-" + entry_data.fields["numpages"]
        publication["Publishing Status"] = "Published"
        publication["Year"] = entry_data.fields["year"]
        #publication["Publisher"] = entry_data.fields["publisher"]
        #publication["Description / Contribution Value"] = 
        publication["URL"] = entry_data.fields["url"]
        publication["Refereed?"] = "Yes"
        #publication["Open Access"] = "Yes"
        #publication["Synthesis?"] = "Yes"
        publication["DOI"] = entry_data.fields["doi"]

        publications["Contributions"]["Publications"]["Journal Articles"].append(publication)

output_root = build_xml_ccv(publications)

# write to file (idented)
ET.indent(output_root)
output_tree = ET.ElementTree(output_root)
output_tree.write("publications.xml", encoding="utf-8", xml_declaration=True, method="xml")
```
Note: some fields are required from the CCV but missing from the bibtex (e.g., contribution percentage, contribution value). In the example, some of thee fields are being reconstructed from the info we do have. The others are left blank.



