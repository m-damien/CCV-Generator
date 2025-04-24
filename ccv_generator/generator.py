import xml.etree.ElementTree as ET
import datetime
from ruamel.yaml.comments import CommentedMap
import re


from ccv_generator.downloader import retrieve_cached_file

# Model with all the ids
ccv_model = ET.parse(retrieve_cached_file('https://ccv-cvc.ca/schema/dataset-cv.xml')).getroot()

# Load the dataset of lov and reference tables (predefined choices)
lov = ET.parse(retrieve_cached_file('https://ccv-cvc.ca/schema/dataset-cv-lov.xml')).getroot()
ref_table = ET.parse(retrieve_cached_file('https://ccv-cvc.ca/schema/dataset-cv-ref-table.xml')).getroot()


def get_lov_table(lookupId):
    """
    Get the List of Values table correspomding to the given lookupId
    """
    global lov
    return lov.find('lov/table[@id="' + lookupId + '"]')

def get_lov(lookupId, value):
    """
    Get the XML lov tag corresponding to the given lookupId and value
    """
    global lov
    table = get_lov_table(lookupId)
    if table is not None:
        for code in table:
            if code.get('englishName').lower() == str(value).strip().lower():
                lovtag = ET.Element("lov")
                lovtag.set('id', code.get('id'))
                lovtag.text = code.get('englishName')
                return lovtag
        # Possible values (if more than 10, add a ellipsis)
        possible_values = ""
        if len(table) > 10:
            possible_values = [code.get('englishName') for code in table[:10]]
            possible_values.append("...")
        else:
            possible_values = [code.get('englishName') for code in table]

        print("ERROR: Could not find the value " + value + ". Should be one of the following:" + str(possible_values))
    else:
        print("ERROR: Could not find the lov for lookupId " + lookupId)
    return None

def get_reference_table(lookupId):
    """
    Get the reference table corresponding to the given lookupId
    """
    global ref_table
    return ref_table.find('reference/listCombination/refTable[@id="' + lookupId + '"]')


def get_reference(lookupId, value):
    """
    Get the XML refTable tag corresponding to the given lookupId and value
    """
    table = get_reference_table(lookupId)
    reftag = ET.Element("refTable")

    if table is not None:
        for valuetag in table:
            if valuetag.get('englishDescription').lower() == value.strip().lower():
                reftag.set('refValueId', valuetag.get('id'))

                schema_table = ref_table.find('reference/schema/table[@id="' + lookupId + '"]')

                linkedWiths = []

                # Look at the linked fields
                linkedValues = schema_table.find("field[@id='" + valuetag.get('id') + "']").findall("fieldValue")
                for idx, linkedField in enumerate(schema_table.findall("value[@id='-1']")):
                    if len(linkedValues) <= idx:
                        break

                    # Get the corresponding value in that other table
                    linkedValue = linkedValues[idx]

                    # Figure out what is the other table (matching by name, could not figure out another way)
                    name = linkedField.get('englishName')
                    is_lov = name.endswith(" (List Of Values)")
                    name = re.sub(r'\([^)]*\)', '', name).strip() # remove the text between parantheses

                    # Find the corresponding table
                    if is_lov:
                        lov_table = lov.find('lov/table[@englishName="' + name + '"]') 
                        if lov_table is not None:
                            for res in lov_table.findall("code[@id='" + linkedValue.get('id') + "']"):
                                linkedWiths.append({"id": lov_table.get('id'), "value": res.get('englishName'), "label": lov_table.get('englishName')})
                    else:
                        linkedTable = ref_table.find('reference/schema/table[@englishName="' + name + '"]')
                        if linkedTable is not None:
                            # Search in the corresponding refTable
                            linkedRefTable = ref_table.find('reference/listCombination/refTable[@id="' + linkedTable.get('id') + '"]')
                            if linkedRefTable is not None:
                                for res in linkedRefTable.findall("value[@id='" + linkedValue.get('id') + "']"):
                                    linkedWiths.append({"id": linkedRefTable.get('id'), "value": res.get('englishDescription'), "label": linkedTable.get('lowestEnglishName')})


                linkedWiths.append({"id": table.get('id'), "value": valuetag.get('englishDescription'), "label": schema_table.get('englishName')})

                for linkedWith in linkedWiths:
                    linkedWithTag = ET.Element("linkedWith")
                    linkedWithTag.set('label', linkedWith.get('label'))
                    linkedWithTag.set('value', linkedWith.get('value'))
                    linkedWithTag.set('refOrLovId', linkedWith.get('id'))
                    reftag.append(linkedWithTag)

                return reftag
                
                

    print("ERROR: Could not find the value " + value + " in the reference table " + lookupId)

    return None
            


def add_data(root, value, field):
    """
    Add data to the XML tree using the correct CCV format depending on the field type
    """
    datatype = field.get('dataType')
    if datatype == "00000000000000000000000000000001": # string
        valuetag = ET.SubElement(root, "value")
        valuetag.set('type', 'String')
        if value is not None: valuetag.text = value
    elif datatype == "00000000000000000000000000000013": # Bilingual field
        valuetag = ET.SubElement(root, "value")
        valuetag.set('type', 'Bilingual')
        if value is not None: valuetag.text = value
        bilingualtag = ET.SubElement(root, "bilingual")
        englishtag = ET.SubElement(bilingualtag, "english")
        if value is not None: englishtag.text = value
    elif datatype == "00000000000000000000000000000007": # number
        valuetag = ET.SubElement(root, "value")
        valuetag.set('type', 'Number')
        if value is not None: valuetag.text = value
    elif datatype == "00000000000000000000000000000006": # lov (choice among a predefined list)
        if value is not None:
            lookupId = field.get('lookupId')
            lov = get_lov(lookupId, value)
            if lov is not None:
                root.append(lov)
    elif datatype == "00000000000000000000000000000009": # YearMonth
        valuetag = ET.SubElement(root, "value")
        valuetag.set('type', 'YearMonth')
        valuetag.set('format', 'yyyy/MM')
        if value is not None: valuetag.text = value
    elif datatype == "00000000000000000000000000000014": # Year
        valuetag = ET.SubElement(root, "value")
        valuetag.set('type', 'Year')
        valuetag.set('format', 'yyyy')
        if value is not None: valuetag.text = value
    elif datatype == "00000000000000000000000000000002":
        # <value format="yyyy-MM-dd" type="Date"></value>
        valuetag = ET.SubElement(root, "value")
        valuetag.set('type', 'Date')
        valuetag.set('format', 'yyyy-MM-dd')
        if value is not None: valuetag.text = value
    elif datatype == "00000000000000000000000000000010":
        valuetag = ET.SubElement(root, "value")
        valuetag.set('type', 'MonthDay')
        valuetag.set('format', 'MM/dd')
        if value is not None: valuetag.text = value
    elif datatype == "00000000000000000000000000000008": # refTable
        if value is not None:
            refTag = get_reference(field.get('lookupId'), value)
            refTag.set('label', root.get('label'))
            if refTag is not None:
                root.append(refTag)
    else:
        print("Unknown datatype for " + field.get('englishName') + " : " + datatype)

def get_comment(field):
    """
    Get the instructions associated with the field
    """
    dates = {
        '00000000000000000000000000000009': 'yyyy/MM',
        '00000000000000000000000000000014': 'yyyy',
        '00000000000000000000000000000002': 'yyyy-MM-dd',
        '00000000000000000000000000000010': 'MM/dd'
    }
    datatype = field.get('dataType')
    # Possible values (if more than 10, add a ellipsis)
    if datatype == "00000000000000000000000000000006":
        lookupId = field.get('lookupId')
        table = get_lov_table(lookupId)
        if len(table) > 10:
            return "e.g., " + ", ".join([code.get('englishName') for code in table[:3]]) + "... Full list: https://ccv-cvc.ca/schema/dataset-cv-lov.xml"
        
        return "One of: " + ", ".join([code.get('englishName') for code in table])
    elif datatype in dates:
        return "In format " + dates[datatype]
    elif datatype == "00000000000000000000000000000008":
        refTable = get_reference_table(field.get('lookupId'))
        if len(refTable) > 10:
            return "e.g., " + ", ".join([code.get('englishDescription') for code in refTable[:3]]) + "... Full list: https://ccv-cvc.ca/schema/dataset-cv-ref-table.xml"
        else:
            return "One of: " + ", ".join([code.get('englishDescription') for code in refTable])
    return None

def get_label(element):
    """
    Get the label of the element. If there is an englishName attribute, use it. Otherwise, use the label attribute so that it is compatible with both dataset-cv and a CCV XML file
    """
    if element.get("englishName") is not None:
        return element.get("englishName")
    return element.get("label")

def is_enabled(element):
    """
    Check if the element is enabled (status="Enabled") in the template
    """
    if element.get("status") is not None:
        return element.get("status") == "Enabled"
    return True

def get_value(element):
    """
    Get the value of an XML element in a CCV XML file
    """
    if element.find("lov") is not None:
        return element.find('lov').text
    elif element.find('refTable') is not None:
        refTable = element.findall('refTable/linkedWith')
        if len(refTable) > 0:
            return refTable[-1].get('value')
    elif element.find('value') is not None:
        val = element.find('value').text
        if val is not None:
            return val
    return None

def build_xml_ccv(data, tree_model=ccv_model, output_root=None):
    """
    Build a CCV XML file from a dictionary of data. The data should follow the exact structure of the XML files generated by CCV. 
    tree_model is a model CCV XML file. Should most likely never be changed unless the CCV XML format changes.
    """
    if output_root is None:
        output_root = ET.Element("generic-cv:generic-cv")
        output_root.set('xmlns:generic-cv', 'http://www.cihr-irsc.gc.ca/generic-cv/1.0.0')
        output_root.set('lang', 'en')
        output_root.set('dateTimeGenerated', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    for tag in tree_model:
        label = get_label(tag)
        if tag.tag == 'section':
            if label in data:
                is_list = tag.get('sortOnField1') is not None

                if is_list and isinstance(data[label], list):
                    for item in data[label]:
                        section = ET.SubElement(output_root, "section")
                        section.set('id', tag.get('id'))
                        section.set('label', label)
                        build_xml_ccv(item, tag, section)
                else:
                    new_data = data[label]
                    section = ET.SubElement(output_root, "section")
                    section.set('id', tag.get('id'))
                    section.set('label', label)
                    build_xml_ccv(new_data, tag, section)
        elif tag.tag == 'field':
            field = ET.SubElement(output_root, "field")
            field.set('id', tag.get('id'))
            field.set('label', label)
            data_to_add = None
            if label in data:
                data_to_add = data[label]
            add_data(field, data_to_add, tag)
        elif tag.tag == 'constraint':
            None

    return output_root

def parse_xml_ccv(tree_model, section_filter=[], add_comments=True, data=CommentedMap(), path="."):
    """
    Parse a CCV XML file and return a dictionary with the data. The data will follow the exact structure of the XML files generated by CCV.
    section_filter is a list of section names to filter the data. For example, ["Contributions", "Publications", "Conference Publications"] will only parse conference publications. If the list is empty, all sections will be parsed.
    data and path are used for recursion and should not be changed.
    """
    last_list_name = None
    for tag in tree_model:
        if tag.tag == 'section' and is_enabled(tag):
            if len(section_filter) > 0 and get_label(tag) != section_filter[0]:
                continue

            new_path = path + "/section[@englishName='" + get_label(tag) + "']"

            is_list = ccv_model.find(new_path).get('sortOnField1') is not None
            
            sub_data = parse_xml_ccv(tag, section_filter[1:], add_comments, CommentedMap(), new_path)

            if is_list and last_list_name == get_label(tag):
                if isinstance(data, list):
                    data[-1][get_label(tag)].append(sub_data)
                else:
                    data[get_label(tag)].append(sub_data)
            else:
                if isinstance(data, list):
                    data.append(CommentedMap({get_label(tag): [sub_data] if is_list else sub_data}))
                else:
                    data[get_label(tag)] = [sub_data] if is_list else sub_data

            last_list_name = get_label(tag)

        elif tag.tag == 'field' and is_enabled(tag):
            # Find the corresponding field in the model cv
            model_field = ccv_model.find(path + "/field[@englishName='" + get_label(tag) + "']")

            comment = get_comment(model_field)
            if model_field.get("englishDescription") is not None:
                comment = (comment if comment is not None else "") + " (" + model_field.get("englishDescription").replace("\n", " ") + ")"

            data[get_label(tag)] = get_value(tag)
            if add_comments and comment is not None:
                data.yaml_add_eol_comment(comment, key=get_label(tag))
                

    return data