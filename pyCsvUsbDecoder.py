import sys
import csv
import argparse
import itertools

class usb_state:
    SE0 = 0
    J = 1
    K = 2
    SE1 = 3

class usb_state_count:
    state = usb_state.SE1
    count = 0

    def __init__(self, state, count):
        self.state = state
        self.count = count

def decode_usb_wire(data_plus, data_minus):
    if not data_plus and not data_minus:
        return usb_state.SE0
    elif not data_plus:
        return usb_state.K
    elif not data_minus:
        return usb_state.J
    else:
        return usb_state.SE1

def read_file(file_name, data_plus_col, data_minus_col, ignore_less_than):
    values = []
    with open(file_name, 'rb') as csv_file:
        csv_reader = csv.reader(csv_file)

        prev = None
        count = 0
        for row in csv_reader:
            try:
                data_plus = float(row[data_plus_col]) > 1.7
                data_minus = float(row[data_minus_col]) > 1.7
                decoded = decode_usb_wire(data_plus, data_minus)
                if prev is not None and prev == decoded:
                    count += 1
                else:
                    if prev is not None:
                        if count >= ignore_less_than:
                            if len(values) > 1 and values[len(values)-1].state == prev:
                                values[len(values)-1].count += count
                            else:
                                values.append(usb_state_count(prev, count))
                    count = 1
                    prev = decoded
            except ValueError:
                pass
    return values

def decode_nrzi(bits):
    previous = False
    oneCount = 0
    for bit in bits:
        if not previous and bit:
            oneCount = 0
            yield False
        elif not previous:
            oneCount += 1
            if oneCount == 6:
                oneCount = 0
            else:
                yield True
        elif not bit:
            oneCount = 0
            yield False
        else:
            oneCount += 1
            if oneCount == 6:
                oneCount = 0
            else:
                yield True
        previous = bit

def main():
    parser = argparse.ArgumentParser(description='pyCsvUsbDecoder.py - CSV USB 1.1 signal decoder', prog='UsbDecoder')

    parser.add_argument(
        '--input-file', '-i',
        help='Input file')

    parser.add_argument(
        '--output-file', '-o',
        help='Output file')

    parser.add_argument(
        '--data-plus-column', '-dp',
        type=int,
        help='Data plus column')

    parser.add_argument(
        '--data-minus-column', '-dm',
        type=int,
        help='Data minus')

    parser.add_argument(
        '--error-values-margin', '-m',
        type=int,
        help='Ignore values if there is less than provided number od samples')

    args = parser.parse_args()
    print 'Input file: ', args.input_file
    print 'Output file: ', args.output_file
    values = read_file(args.input_file, args.data_plus_column, args.data_minus_column, args.error_values_margin)
    output_file = open(args.output_file,'w')

    i = 0
    while i < len(values):
        # check if it could be begin of packet
        if values[i].state != usb_state.J or \
           values[i+1].state != usb_state.K or\
           values[i+2].state != usb_state.J or \
           values[i+3].state != usb_state.K or \
           values[i+4].state != usb_state.J or \
           values[i+5].state != usb_state.K or \
           values[i+6].state != usb_state.J or \
           values[i+7].state != usb_state.K:
            i += 1
            continue
          
        # make sure length of values is correct- first K J K J K J should have same size(almost...)
        if values[i+1].count - values[i+2].count > args.error_values_margin:
            i += 1
            continue
        if values[i+2].count - values[i+3].count > args.error_values_margin:
            i += 1
            continue
        if values[i+3].count - values[i+4].count > args.error_values_margin:
            i += 1
            continue
        if values[i+4].count - values[i+5].count > args.error_values_margin:
            i += 1
            continue
        if values[i+5].count - values[i+6].count > args.error_values_margin:
            i += 1
            continue

        one_value_length = (values[i+1].count + values[i+2].count + values[i+3].count + values[i+4].count + values[i+5].count + values[i+6].count) / 6
        
        i += 1

        bits = []
        while i<len(values) and values[i].state != usb_state.SE0:
            if values[i].state == usb_state.J:
                number_of_bits = int(round(float(values[i].count)/one_value_length))
                bits += number_of_bits * [False]
            elif values[i].state == usb_state.K:
                number_of_bits = int(round(float(values[i].count)/one_value_length))
                bits += number_of_bits * [True]
            elif values[i].state == usb_state.SE1:
                break
            i += 1

        bits_decoded = decode_nrzi(bits)

        count = 0
        value = 0
        for bit in bits_decoded:
            value += bit << count
            count += 1
            if count == 8:
                output_file.write(hex(value)[2:])
                value = 0
                count = 0
        output_file.write('\n')
        print 'Packet decoded @', i

    output_file.close()
    print 'Done'

if __name__ == "__main__":
    main()
