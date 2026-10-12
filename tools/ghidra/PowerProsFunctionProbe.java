// SPDX-License-Identifier: GPL-3.0-or-later
// Focused static probe of an original PowerPC function extracted from the user's DOL.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

public class PowerProsFunctionProbe extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] arguments = getScriptArgs();
        if (arguments.length != 4) throw new IllegalArgumentException("Expected address, function name, original extracted bytes and output directory");
        Address entry = toAddr(arguments[0]);
        String language = currentProgram.getLanguageID().toString();
        if (!language.startsWith("PowerPC:BE:32:")) throw new IllegalStateException("Unexpected language: " + language);
        byte[] original = Files.readAllBytes(Path.of(arguments[2]));
        byte[] loaded = new byte[original.length];
        if (currentProgram.getMemory().getBytes(entry, loaded) != original.length || !Arrays.equals(original, loaded)) {
            throw new IllegalStateException("Imported bytes differ from original extracted DOL function");
        }
        disassemble(entry);
        Function function = getFunctionAt(entry);
        if (function == null) function = createFunction(entry, arguments[1]);
        if (function == null) throw new IllegalStateException("No function recovered at requested address");
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException("Decompiler could not open imported program");
            DecompileResults results = decompiler.decompileFunction(function, 30, monitor);
            if (!results.decompileCompleted() || results.getDecompiledFunction() == null) {
                throw new IllegalStateException("Decompiler failed: " + results.getErrorMessage());
            }
            String pseudocode = results.getDecompiledFunction().getC();
            if (pseudocode.isBlank()) throw new IllegalStateException("Empty pseudocode");
            Path output = Path.of(arguments[3]);
            Files.createDirectories(output);
            Files.writeString(output.resolve("pseudocode.c"), pseudocode, StandardCharsets.UTF_8);
            StringBuilder assembly = new StringBuilder();
            InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
            int count = 0;
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                assembly.append(instruction.getAddress()).append(" ").append(instruction).append("\n");
                count++;
            }
            if (count == 0) throw new IllegalStateException("Empty assembly");
            Files.writeString(output.resolve("assembly.txt"), assembly.toString(), StandardCharsets.UTF_8);
            Files.writeString(output.resolve("probe-status.txt"),
                "language=" + language + "\nentry=" + entry + "\nloaded_bytes_match=true\nextracted_bytes=" + original.length +
                "\ninstructions=" + count + "\npseudocode_observed=true\n", StandardCharsets.UTF_8);
            println("POWERPROS_GHIDRA_PPC_OK entry=" + entry + " language=" + language + " instructions=" + count);
        } finally {
            decompiler.dispose();
        }
    }
}
