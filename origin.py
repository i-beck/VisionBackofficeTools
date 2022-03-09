import telnetlib
import xmltodict


def tn_login_start():
    global WAIT_SEC
    global TELNET

    host = VISION_CREDENTIALS.ip
    user = VISION_CREDENTIALS.user
    password = VISION_CREDENTIALS.pswd
    port = VISION_CREDENTIALS.port

    # wait_sec = 1 #this is how long to delay when waiting for a response

    try:
        TELNET = telnetlib.Telnet(host, port)
        TELNET.read_until(b"login: ", 5)
        TELNET.write(user.encode("ascii") + b"\n")
        TELNET.read_until(b"Password: ", 5)
        TELNET.write(password.encode("ascii") + b"\n")
    except (TimeoutError, ConnectionRefusedError) as err:
        raise PermissionError("Invalid Vision Credientials Used. (IP/Port Mismatch)") from err

    if b"Invalid domain/user/password" in TELNET.read_until(b"UniData Release", 5):
        TELNET.close()
        raise PermissionError("Invalid Vision Credientials Used.")
    TELNET.write(b"\n")
    TELNET.write(b"\n")
    TELNET.write(b"\n")
    TELNET.write(b"\n")


def tn_vision_dump_to_ecl():

    while b"1 record listed" not in TELNET.read_until(b"\n:", 0.1):
        TELNET.write("\x03Q\n\n\nLIST RELEASE SAMPLE 1\n".encode("ascii"))
    TELNET.read_until(b"\n:", 0.1)

    return


def tn_vision_close_connection():
    global TELNET
    tn_vision_dump_to_ecl()
    try:
        TELNET.write(b"BYE\n\n")
        TELNET.write(b"\n")
        TELNET.read_until(b"cgfdg~fdgdf~gdfg~fdg", 1)
        TELNET.close()
    except ConnectionResetError as _err:
        # print(_err)
        TELNET.close()
        TELNET = None
        return
    print("Vision Software disconnect Failed, attempting socket disconnect...")
    TELNET.close()
    TELNET = None


def tn_wait_write(tn_wait, tn_write, new_wait_sec=WAIT_SEC):  # usage: tn_write = "what you want to write now" tn_wait = "string your waiting for next"
    tn_wait = tn_wait.encode()
    tn_input = (tn_write + "\r\n").encode()
    _results_print = TELNET.read_until(tn_wait, (new_wait_sec))
    # time.sleep(1)
    if TN_DEBUG:
        print(_results_print.decode("ascii", "ignore"))  # debug, turn off when done

    TELNET.write(tn_input)


def unidata_querybuilder(
    voc_filename,
    return_fields_list,
    query_expression="",
    sselect=None,
    raw_query=None,
    unirecord_ids=None,
    tn_keepalive=False,
    sample=None,
    get_lquery=False,
    get_squery=False,
    timeout_time_int=1500,
):
    """[summary]

    Args:
        voc_filename (str): VOC Filename found from UniQuery System that you would like information from.
        return_fields_list (list): A list of fields you would like returned from the VOC Filename.
        query_expression (str, optional): Unidata List Query - Allows modification to final info returned. Defaults to "".
        sselect (list, tuple, or str, optional): SSELECT's data from UniQuery. Uses iterable for sucessive select statements, strings for raw querys or dict. Dict Example: {'EXT_CUST': ['001', '002' ], 'DATE': {'params':"01/29/10", 'andor':'and', 'oper':">"} } . Defaults to None.
        raw_query (str, optional): Only Submits a single raw, unformatted string to UniQuery. Defaults to None.
        unirecord_ids (str, list, optional): Takes a string or list that match a records '@id' field of the VOC file. Defaults to None.
        tn_keepalive (bool, optional): If you would like to control telnet login from out of this scope, set to True. Defaults to False.
        sample (int, optional): Returns first N number of samples from the query. Defaults to None.
        get_lquery (bool, optional): If set to True, retrieves no data except UniQuery String for LIST request. Defaults to False.
        get_squery (bool, optional): If set to True, retrieves no data except UniQuery String for first SSELECT request. Defaults to False.
        timeout_time_int (int, optional): Change the Max Timeout time for a query from the UniData system. Defaults to 1500.

    Returns:
        Tuple: Rows of data in OrderedDict format.
    """

    unidata_errors = {
        "No data retrieved from": "No data returned for select query.",
        "Illegal attribute name:": "Invalid Field Specified in fields list.",
        "Illegal attribute:": "Invalid Field Specified.",
        "does not exist in VOC file.": "Invalid VOC file specified.",
        "No records listed.": "No Results found from list Query.",
        "Malformed XML from unidata query:": "Malformed XML generated from UniData Query",
        "Malformed statement in select query:": "Malformed statement in UniData SSELECT query.",
    }

    # data_dict = {}
    not_a_verb = "\r\nmasdsajghdasjkdas"

    if not tn_keepalive:
        tn_login_start()
        tn_wait_write("", "")
        tn_wait_write("Verify Invoice", "END")
        tn_wait_write("ENTER MENU 20 PASSWO", "ECL")
        # dumptoECL()
        # tn_vision_dump_to_ecl()

    tn_wait_write("", "")
    opt_records_id_string = ""

    # tn_wait_write(":","")
    return_fields_string = " ".join(return_fields_list)

    if unirecord_ids is not None:
        if isinstance(unirecord_ids, str):
            if " " not in unirecord_ids and '"' not in unirecord_ids:
                opt_records_id_string = f'"{unirecord_ids}"'
            else:
                opt_records_id_string = unirecord_ids
        else:
            opt_records_id_string = " ".join((f'"{x}"' for x in unirecord_ids))

    telnet_results = ""
    try:
        if sselect is not None:

            if isinstance(sselect, (list, tuple)):
                sselect = list(sselect)
                for i, squery in enumerate(sselect):
                    if isinstance(squery, dict):
                        sselect[i] = unidata_querybuilder(voc_filename, return_fields_list, query_expression, squery, tn_keepalive=True, get_squery=True)

                for squery in sselect:
                    if "SELECT" not in squery.upper() or voc_filename.upper() not in squery.upper():
                        print("Malformed statement in select query: '{}'".format(squery))
                        raise ValueError("Malformed statement in select query:")

                    if get_squery:
                        continue
                    tn_wait_write("", squery.upper() + not_a_verb)
                    err_check_results = ecl_string_scrub(tn_return_wait_write("Not a verb", "", timeout_time_int / 3))
                    for uerr in unidata_errors:
                        if uerr in err_check_results:
                            raise ValueError(uerr)

                if get_squery:
                    return sselect

            elif isinstance(sselect, dict):
                sselect_string = "SSELECT {} ".format(str(voc_filename).upper())
                for select_key in sselect:
                    if isinstance(sselect[select_key], str):
                        sselect_string += '{withand} WITH {skey} = "{param}" '.format(
                            withand=("AND" if " WITH " in sselect_string else ""), skey=select_key.upper(), param=sselect[select_key].upper()
                        )
                    elif isinstance(sselect[select_key], (list, tuple)):
                        sselect_string += "{withand} WITH {skey} = {params} ".format(
                            withand=("AND" if " WITH " in sselect_string else ""),
                            skey=select_key.upper(),
                            params=" ".join(['"{}"'.format(x) for x in sselect[select_key]]),
                        )
                    elif isinstance(sselect[select_key], dict):
                        andor = sselect[select_key].get("andor")
                        oper = sselect[select_key].get("oper")
                        params = sselect[select_key].get("params")
                        if not isinstance(params, (list, tuple)):
                            params = [params]
                        sselect_string += "{withand} WITH {skey} {oper} {params} ".format(
                            withand=((andor.upper() if andor is not None else "AND") if " WITH " in sselect_string else ""),
                            skey=select_key.upper(),
                            params=" ".join(['"{}"'.format(x) for x in params]),
                            oper=(oper.upper() if oper is not None else "="),
                        )

                if get_squery:
                    return sselect_string

                tn_wait_write("", sselect_string.upper() + not_a_verb)
                err_check_results = ecl_string_scrub(tn_return_wait_write("Not a verb", "", timeout_time_int / 3))
                for uerr in unidata_errors:
                    if uerr in err_check_results:
                        raise ValueError(uerr)

            elif isinstance(sselect, str):
                if "SELECT" not in sselect.upper() or voc_filename.upper() not in sselect.upper():
                    print("Malformed statement in select query: '{}'".format(sselect))
                    raise ValueError("Malformed statement in select query:")

                if get_squery:
                    return sselect
                tn_wait_write("", sselect.upper() + not_a_verb)
                err_check_results = ecl_string_scrub(tn_return_wait_write("Not a verb", "", timeout_time_int / 3))
                for uerr in unidata_errors:
                    if uerr in err_check_results:
                        raise ValueError(uerr)

            else:
                print("'sselect' paramater only supports ('str', 'list', 'tuple', 'dict') but not '{}'".format(type(sselect).__name__))
                raise ValueError("Malformed statement in select query:")

        uniquery = "LIST {filename} {records} {query} {return_fields} {sample} TOXML".format(
            filename=voc_filename,
            records=opt_records_id_string,
            query=query_expression,
            return_fields=return_fields_string,
            sample=f"SAMPLE {str(sample)}" if isinstance(sample, int) else "",
        )

        # print(uniquery)

        uniquery = (uniquery if raw_query is None else (raw_query if " TOXML" in raw_query.upper() else raw_query + " TOXML")).upper()

        if get_lquery:
            return uniquery

        tn_wait_write("", uniquery + not_a_verb)
        # print(uniquery)

        # telnet_results = tn_return_wait_write("</ROOT>","", timeout_time_int)
        telnet_results = tn_return_wait_write("Not a verb", "", timeout_time_int)

        xml_head_string = "<?xml "

        xml_tail_string = "</ROOT>"

        if len(telnet_results) < 1500:
            for uerr in unidata_errors:
                if uerr in telnet_results:
                    raise ValueError(uerr)

        if xml_head_string in telnet_results and xml_tail_string in telnet_results:
            telnet_results = telnet_results[telnet_results.find(xml_head_string) : telnet_results.find(xml_tail_string) + len(xml_tail_string)]
            # print(xmlstring[:xmlstring.find('</ROOT>') + len('</ROOT>') ] )
        # print("hello")
        else:
            print("Malformed XML from unidata query:\n'{}'\nSelect Query: {}\n\n\tUnable to Parse.".format(uniquery, sselect))
            raise ValueError("Malformed XML from unidata query:")
    except ValueError as err:
        error_test = unidata_errors.get(str(err))
        if error_test is None:
            raise
        print("No Results Error: {}".format(error_test))
        if not tn_keepalive:
            tn_wait_write("", "")
            tn_wait_write("", "BYE")
        else:
            tn_wait_write("", "")
        return tuple()
    if not tn_keepalive:
        tn_wait_write("", "")
        tn_wait_write("", "BYE")
    # print(telnet_results)
    telnet_results = xmltodict.parse(telnet_results, namespace_separator=" ")

    if telnet_results is None or telnet_results.get("ROOT") is None or telnet_results["ROOT"].get(voc_filename.upper()) is None:
        return tuple()

    telnet_results = telnet_results["ROOT"][voc_filename.upper()]

    if not isinstance(telnet_results, list):
        return (telnet_results,)

    return tuple(telnet_results)
