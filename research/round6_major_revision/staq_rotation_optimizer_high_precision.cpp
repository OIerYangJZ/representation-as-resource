// Generic high-precision CLI wrapper around staq's public rotation-folding API.
// Relative to upstream src/tools/rotation_optimizer.cpp, this wrapper requests
// 17-digit stream precision. The source tree used to build it also carries the
// disclosed staq_double_precision.patch: real literals are parsed with stod
// instead of stof, and AST numeric output uses double::max_digits10 instead of
// 15 digits. No rotation-folding logic is changed.
#include <iomanip>
#include <iostream>

#include <third_party/CLI/CLI.hpp>

#include "qasmtools/parser/parser.hpp"
#include "staq/optimization/rotation_folding.hpp"

int main(int argc, char** argv) {
    using namespace staq;
    using qasmtools::parser::parse_stdin;

    bool no_correction = false;
    CLI::App app{"QASM rotation optimizer (17-digit output wrapper)"};
    app.add_flag("--no-phase-correction", no_correction,
                 "Turns off global phase corrections");
    CLI11_PARSE(app, argc, argv);

    auto program = parse_stdin();
    if (!program) {
        std::cerr << "Parsing failed\n";
        return 1;
    }
    optimization::fold_rotations(*program, {!no_correction});
    std::cout << std::setprecision(17) << *program;
    return 0;
}
