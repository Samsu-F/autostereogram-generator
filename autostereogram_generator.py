#!/usr/bin/env python3

import sys
import random
import argparse
import typing
import textwrap


def char_to_depth_value(c: str) -> int:
    assert len(c) == 1
    if c == ' ':
        return 0
    ascii_ord = ord(c)
    if ascii_ord >= 48 and ascii_ord <= 57: # numeric character
        return ascii_ord - 48 # '0' -> 0 etc
    if ascii_ord >= 97 and ascii_ord <= 122:    # a-z
        return ascii_ord - 96 # 'a' -> 1, 'b' -> 2, etc
    if ascii_ord >= 65 and ascii_ord <= 90:     # A-Z
        return 64 - ascii_ord # 'A' -> -1, 'B' -> -2, etc
    else:
        raise Exception(f"Invalid character for representing depth: found '{c}', ord('{c}')={ord(c)}")



def parse_depth_map_file(filename: str, width: int, height: int, depth_rescale_factor: float) -> list[list[int]]:
    with open(filename, "r") as file:
        lines = file.read().splitlines()
        if len(lines) == 0:
            print("Error: depthfile is empty, exiting.", file=sys.stderr)
            sys.exit(1)
        max_line_length = max([len(l) for l in lines])
        if width is None:
            width = max_line_length
        if height is not None:
            if height <= len(lines):
                lines = lines[:height]
            else:   # height > len(lines)
                # center vertically
                total_lines_to_add = height - len(lines)
                lines_above = total_lines_to_add // 2
                lines_below = total_lines_to_add - lines_above
                lines = ['']*lines_above + lines + ['']*lines_below
        lines = [f"{l:<{max_line_length}}" for l in lines]  # fill all lines to the same length
        lines = [f"{l[:width]:^{width}}" for l in lines]    # trim or pad (centered) every line to wdth
        result = [[char_to_depth_value(char) for char in l] for l in lines] # map to integer values
        result = [[round(x * depth_rescale_factor) for x in l] for l in result] # rescale and round to integer
        assert len(result) == height or height is None
        assert len(result) != 0
        for x in result:
            assert len(x) == width or width is None
        return result




def pattern_from_file(filename: str, height: int, shift: int) -> list[list[str]]:
    with open(filename, "r") as file:
        lines = file.read().splitlines()
        lines = lines[:height]
        result = [[char for char in l] for l in lines]
        for line_number, line in enumerate(result):
            if len(line) < shift:
                print(f"Error: Pattern too short, line {line_number} of pattern file is shorter than SHIFT.",
                "Exiting.",
                sep='\n',
                file=sys.stderr)
                sys.exit(1)
        return result



# patternwidth should be greater than the shift, surplus is needed to fill in holes
# shift + width is guaranteed to be enough even in the most ridiculous circumstances
def random_pattern(height: int, patternwidth: int) -> list[list[str]]:
    assert patternwidth >= 2
    char_pool = list("aAbBcdDeEfFgGhHiJKLmMnNOPqQrRstTuVwXyZ12346789@#%$&/\\?^ ,;.:-_+*~\"!=|{}[]()><'`")
    result = []
    for i in range(height):
        line = []
        while len(line) < patternwidth:
            random.shuffle(char_pool)
            line += char_pool
        result.append(line[:patternwidth])
    return result



def validate_shift_arg(shift: int, depthmap: list[list[int]]) -> None:
    max_abs_val = max([abs(val) for line in depthmap for val in line])
    if shift <= max_abs_val:
        print("Error: SHIFT has to be greater than the greatest absolute value in the depthmap.",
                f"Found SHIFT = {shift} and greatest absolute in depthmap = {max_abs_val}.",
                "Use option --help for tips on choosing a good SHIFT value.",
                "Exiting.",
                sep='\n',
                file=sys.stderr)
        sys.exit(1)
    elif shift < 2:
        print("Error: shift has to be 2 or greater.",
                f"Found {shift = }",
                "Exiting.",
                sep='\n',
                file=sys.stderr)
        sys.exit(1)



def validate_surplus(surplus: list[str], line_number: int) -> None:
    if len(surplus) == 0:
        print(f"Error: ran out of pattern surplus, pattern file does not contain enough characters in line {line_number}.",
                "Exiting.",
                sep='\n',
                file=sys.stderr)
        sys.exit(1)



def generate_autostereogram(depth_map: list[list[int]], shift: int, pattern: list[list[str]]) -> str:
    assert len(pattern) == len(depth_map)
    assert len(depth_map) >= 1
    assert shift >= 2
    assert len(pattern[0]) > shift
    result = ""

    for li, dml in enumerate(depth_map): # line index, depth map line
        result_line, surplus = pattern[li][:shift], pattern[li][shift:]
        result_line += [None] * len(dml)
        for x, elevation in enumerate(dml):
            if result_line[x] is None:
                validate_surplus(surplus, li)
                result_line[x] = surplus[0]
                surplus = surplus[1:]
            x_next_repetition = x + shift - elevation
            result_line[x_next_repetition] = result_line[x]
        for x in range(len(dml), len(dml) + shift): # clean up the last cycle
            if result_line[x] is None:
                validate_surplus(surplus, li)
                result_line[x] = surplus[0]
                surplus = surplus[1:]
        assert None not in result_line
        result += ''.join(result_line) + '\n'
    return result



def positive_int(arg_val):
    try:
        result = int(arg_val)
        if result > 0:
            return result
    except:
        pass
    raise argparse.ArgumentTypeError(f"invalid positive int value: '{arg_val}'")



def parse_args() -> argparse.ArgumentParser:
    argparser = argparse.ArgumentParser(
                    # prog='autostereogram-generator'
                    description='Generate ASCII autostereograms',
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    epilog=textwrap.dedent('''
                        Depth map file syntax:
                          In the depth map, the elevation of a point is represented by a number. The higher the number, the
                          more elevated a point is, i.e. it appears to be nearer.
                          A '0' character or a space represents the elevation of the neutral background plane.
                          Alhabetical characters can be used as an alternative to numbers. An 'a' is equivalent to the
                          number 1, b=2, ... z=26. Using alphabetical characters is the only way to represent elevations
                          greater than 9.
                          Similarly, uppercase letters can be used to represent negative elevation (meaning a point appears
                          further back than the background plane). A=-1, B=-2, ..., Z=-26.

                        Pattern file:
                          Each line is used as the repeating pattern for the corresponding line of the generated
                          autostereogram. Irrespective of the depthmap used, every line needs to be at least SHIFT
                          characters long and can be arbitrarily longer. However, due to the parallax, if there is a point
                          with greater elevation to the left of a point with lower elevation, the right eye is able to see
                          a part of the background that is hidden to the left eye. These spots need to be filled with
                          additional characters. Therefore a surplus of pattern characters is needed, so in practice,
                          the lines in the pattern files need to be longer to have enough characters to fill all of the
                          holes.

                        General tips for best results:
                        - The smaller your pupils are, the easier it is to see the 3D image. Turning on your room lights,
                          setting your display brightness to the maximum and using light mode (eww!) may therefore be
                          beneficial.
                        - The optimal SHIFT value depends on many factors, such as display size and resolution, font and
                          font size, your distance from the display, the magnitude of the elevations, your experice width
                          autostereograms, personal preference and many more. It is worth it to play around with diffenent
                          values until you find one that works for you. Depending on your circumstances, this value could
                          very well be in the single digits or in the hundreds.
                        - If you see double images (or even more), your SHIFT value is too small. Your brain is aligning
                          each character not with its respective copy in the next cycle but the one in the second next or
                          even later cycle. Try doubling the SHIFT value.
                        - Leave enough background around the subjects of your images, as it is difficult to see things near
                          the edges of the image.
                        - If you have space left on your display, increase the width and height for a greater margin. You
                          will have an easier time switching into the 3D vision if there is a greater margin of background
                          supporting the optical illusion.
                        - While it is theoretically possible to use elevation levels just barely lowere than SHIFT, doing
                          so will rarely yield good results. It is recommended to use a SHIFT value at significantly bigger
                          than the maximum absolute elevation, at least double.
                          Also try rescaling the elevations of your depth map (--rescale-depth or -r).
                        - In general, greater elevations will be more noticeable once you managed to switch into the
                          3D vision but they will make it harder to switch, especially if they are used for finer details.
                          Try starting with lower absolute elevations and increasing them only if you need them to be more
                          eye-catching.
                        - When using a custom pattern, avoid using the same characters multiple times in a row if possible,
                          and especially avoid immediatly repeating characters.

                        Author & License
                          Written by Samsu-F, 2024.
                          github.com/Samsu-F
                          This software is licensed under the GNU General Public License v3.0
                        ''') # TODO improve explanation
                    )
    argparser.add_argument('depthmap', type=str,
                                help="""The depth map file""")  # mandatory positional argument
    default_shift = 20
    argparser.add_argument('-s', '--shift', required=False, type=positive_int, default=default_shift,
                                help=f"""The number of characters the neutral background plane is shifted by.
                                        This number has to be grater than the greatest absolute value in the depthmap
                                        (multiplied by the rescale-depth factor, if specified).
                                        (default: {default_shift})""")
    argparser.add_argument('-p', '--pattern', metavar='PATTERN-FILE', required=False, type=str,
                                help="""The pattern file. If no pattern file is specified, a random pattern will be used.
                                        Using a custom pattern will most likely not improve the quality of the 3D effect but
                                        is primarily intended as an artistic choice, e.g. to use characters or words that match the
                                        theme of the image.""")
    argparser.add_argument('-x', '--width', required=False, type=positive_int,
                                help="""The width of the output autostereogram. Since the shift is horizontal,
                                        the horizontal portion of the input depth map that can be included is only this width minus SHIFT.
                                        If the specified width is greater than the sum of SHIFT and the length of the longest line in the
                                        depthmap, the image will be centered.
                                        (default: SHIFT + the width of the longest line, i.e. just enough to display the whole depth map)""")
    argparser.add_argument('-y', '--height', required=False, type=positive_int,
                                help="""The height of the generated autostereogram. This is equal to the number of lines of the depthmap
                                        image  that will be included. If the given height is greater than the number of lines in the
                                        depthmap, the image will be centered. (default: include every line)""")
    argparser.add_argument('-r', '--rescale-depth', required=False, type=float, default=1,
                                help="""The rescale factor to multiply all values in the depth map with.
                                        Note that elevation levels in the final result can only be integer values,
                                        so if you rescale by float, the depths will be rounded to the nearest integer.
                                        (default: 1)""")
    return argparser.parse_args()




def main():
    args = parse_args()
    input_width = None  # the width of the input depthmap to use
    if args.width is not None:
        input_width = args.width - args.shift
    depthmap = parse_depth_map_file(args.depthmap, input_width, args.height, args.rescale_depth)
    validate_shift_arg(args.shift, depthmap)
    if args.height is None:
        args.height = len(depthmap)
    if args.width is None:
        input_width = len(depthmap[0]) # depthmap is guaranteed to not be empty
        args.width = input_width + args.shift
    if args.pattern is None:
        pattern = random_pattern(args.height, args.width)
    else:
        pattern = pattern_from_file(args.pattern, args.height, args.shift)

    autostereogram = generate_autostereogram(depthmap, args.shift, pattern)
    print(autostereogram)



if __name__ == "__main__":
    main()
