import argparse
from ruamel.yaml import YAML # ruamel.yaml
import xml.etree.ElementTree as ET
from ccv_generator.generator import ccv_model, parse_xml_ccv, build_xml_ccv

def main():
    parser = argparse.ArgumentParser(description='Generate a CCV XML file from a YAML file. Or export a CCV XML file to a YAML file.')
    parser.add_argument('-i', '--input', type=str, help='The input file. Can be either a CCV XML file or a YAML file.', default=None)
    parser.add_argument('output', type=str, help='The output file. Can be either a CCV XML file or a YAML file.')
    parser.add_argument('-f', '--filter', type=str, help='Filter to parse only a subset of the CCV XML file. Should be a path of the section(s) to parse (e.g., "Contributions/Publications/Conference Publications" to export only Conference Publications)', default=None)
    parser.add_argument('-q', '--quiet', type=bool, help='Avoid adding comments to the generated yaml file', default=False, action=argparse.BooleanOptionalAction)

    args = parser.parse_args()
    data = None

    yaml = YAML()
    yaml.width = 9000
    # Use null when there is no value
    yaml.representer.add_representer(type(None), lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:null', u'null'))


    if args.input is None:
        data = parse_xml_ccv(ccv_model, section_filter=args.filter.split("/") if args.filter is not None else [], add_comments=not args.quiet)
    else:
        if args.input.endswith(".xml"):
            parsed_xml = ET.parse(args.input).getroot()
            data = parse_xml_ccv(parsed_xml, section_filter=args.filter.split("/") if args.filter is not None else [], add_comments=not args.quiet)
        
        if args.input.endswith(".yaml") or args.input.endswith(".yml"):
            with open(args.input, "r") as f:
                data = yaml.load(f)

    if args.output.endswith(".xml"):
        output_root = build_xml_ccv(data)

        # write to file (indented)
        ET.indent(output_root)
        output_tree = ET.ElementTree(output_root)
        output_tree.write(args.output, encoding="utf-8", xml_declaration=True, method="xml")

    if args.output.endswith(".yaml") or args.output.endswith(".yml"):
        with open(args.output, "w") as f:
            yaml.dump(data, f)

if __name__ == "__main__":
    main()