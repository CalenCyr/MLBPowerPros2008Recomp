cmake_minimum_required(VERSION 3.20)
project(PowerProsRuntimeModule LANGUAGES C)
set(CMAKE_C_STANDARD 11)
get_filename_component(PROJECT_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
set(RECOMPCORE "${PROJECT_ROOT}/local/vendor/ModernGekko/vendor/dolphin")
set(POWERPROS_LLVM_DOL_DIR "" CACHE PATH "Experimental: DolRecomp LLVM-backend DOL output (main.h + main_chunks/*.o)")
if(POWERPROS_LLVM_DOL_DIR)
    set(GENERATED_DIR "${POWERPROS_LLVM_DOL_DIR}")
    set(TABLE_DOL_ARGS --dol-dir "${POWERPROS_LLVM_DOL_DIR}")
else()
    set(GENERATED_DIR "${PROJECT_ROOT}/local/generated/dolrecomp/dol")
    set(TABLE_DOL_ARGS)
endif()
set(REL_LAYOUT_DIR "${PROJECT_ROOT}/local/generated/dolrecomp/rel-linked")
set(POWERPROS_LLVM_REL_DIR "" CACHE PATH "Experimental: DolRecomp LLVM-backend linked REL output (runtime_rel.h + runtime_rel_chunks/*.o)")
if(POWERPROS_LLVM_REL_DIR)
    set(REL_GENERATED_DIR "${POWERPROS_LLVM_REL_DIR}")
    list(APPEND TABLE_DOL_ARGS --rel-dir "${POWERPROS_LLVM_REL_DIR}")
else()
    set(REL_GENERATED_DIR "${REL_LAYOUT_DIR}")
endif()
option(POWERPROS_ENABLE_REL "Include experimental fixed-layout REL translation" OFF)
option(POWERPROS_OPTIMIZE_MODULE "Optimize translated code while keeping strict floating-point semantics" OFF)
option(POWERPROS_REUSE_MSVC_REL_OBJECTS "Experimental Clang DOL with preserved MSVC REL objects" OFF)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(TABLES "${CMAKE_CURRENT_BINARY_DIR}/module_tables.inc")
if(POWERPROS_ENABLE_REL)
add_custom_command(OUTPUT "${TABLES}"
    COMMAND Python3::Interpreter "${PROJECT_ROOT}/tools/gen_runtime_module_tables.py" "${TABLES}" ${TABLE_DOL_ARGS}
    DEPENDS "${PROJECT_ROOT}/tools/gen_runtime_module_tables.py"
        "${GENERATED_DIR}/main.h" "${GENERATED_DIR}/main_smc.txt"
        "${PROJECT_ROOT}/local/disc/DATA/sys/main.dol"
        "${REL_GENERATED_DIR}/runtime_rel.h"
        "${REL_LAYOUT_DIR}/linked-analysis.dol" "${REL_LAYOUT_DIR}/layout.json"
        "${RECOMPCORE}/module-template/gen_module_tables.py" VERBATIM)
if(POWERPROS_LLVM_REL_DIR)
    if(POWERPROS_REUSE_MSVC_REL_OBJECTS OR NOT POWERPROS_LLVM_DOL_DIR)
        message(FATAL_ERROR "The LLVM REL experiment requires the LLVM DOL and no MSVC REL reuse")
    endif()
    file(GLOB REL_CHUNKS CONFIGURE_DEPENDS "${REL_GENERATED_DIR}/runtime_rel_chunks/*.o")
    set_source_files_properties(${REL_CHUNKS} PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
    # Memoized REL lookup window: the linked executable sections from layout.json.
    file(READ "${REL_LAYOUT_DIR}/layout.json" REL_LAYOUT)
    string(JSON REL_SECTION_COUNT LENGTH "${REL_LAYOUT}" sections)
    set(REL_LOOKUP_LO 4294967295)
    set(REL_LOOKUP_HI 0)
    math(EXPR REL_LAST "${REL_SECTION_COUNT} - 1")
    foreach(I RANGE ${REL_LAST})
        string(JSON EXEC GET "${REL_LAYOUT}" sections ${I} executable)
        if(EXEC)
            string(JSON START GET "${REL_LAYOUT}" sections ${I} start)
            string(JSON SIZE GET "${REL_LAYOUT}" sections ${I} size)
            math(EXPR END "${START} + ${SIZE}")
            if(START LESS REL_LOOKUP_LO)
                set(REL_LOOKUP_LO ${START})
            endif()
            if(END GREATER REL_LOOKUP_HI)
                set(REL_LOOKUP_HI ${END})
            endif()
        endif()
    endforeach()
    math(EXPR REL_LOOKUP_SLOTS "(${REL_LOOKUP_HI} - ${REL_LOOKUP_LO} + 3) / 4")
    math(EXPR REL_LOOKUP_BASE "${REL_LOOKUP_LO}" OUTPUT_FORMAT HEXADECIMAL)
    set(REL_DISPATCH llvm_rel_dispatch.c)
else()
file(GLOB REL_CHUNKS CONFIGURE_DEPENDS "${REL_GENERATED_DIR}/runtime_rel_chunks/*.c")
set(REL_DISPATCH rel_dispatch.c)
endif()
if(POWERPROS_REUSE_MSVC_REL_OBJECTS)
    if(NOT CMAKE_C_COMPILER_ID STREQUAL "Clang" OR NOT MSVC OR NOT POWERPROS_OPTIMIZE_MODULE)
        message(FATAL_ERROR "REL object reuse requires optimized clang-cl")
    endif()
    set(REL_OBJECTS)
    foreach(SOURCE IN LISTS REL_CHUNKS)
        get_filename_component(NAME "${SOURCE}" NAME_WE)
        set(OBJECT "${PROJECT_ROOT}/local/build/runtime-module-rel-optimized/gRL8E54_recomp.dir/Release/${NAME}.obj")
        if(NOT EXISTS "${OBJECT}")
            message(FATAL_ERROR "Missing preserved REL object ${OBJECT}")
        endif()
        list(APPEND REL_OBJECTS "${OBJECT}")
    endforeach()
    list(LENGTH REL_OBJECTS OBJECT_COUNT)
    if(NOT OBJECT_COUNT EQUAL 478)
        message(FATAL_ERROR "Expected all 478 preserved REL objects")
    endif()
    set_source_files_properties(${REL_OBJECTS} PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
    set(REL_CHUNKS ${REL_OBJECTS})
endif()
else()
if(POWERPROS_REUSE_MSVC_REL_OBJECTS)
    message(FATAL_ERROR "REL object reuse requires combined module")
endif()
add_custom_command(OUTPUT "${TABLES}"
    COMMAND Python3::Interpreter "${RECOMPCORE}/module-template/gen_module_tables.py"
        "${GENERATED_DIR}/main.h" "${GENERATED_DIR}/main_smc.txt"
        "${PROJECT_ROOT}/local/disc/DATA/sys/main.dol" "${TABLES}"
    DEPENDS "${GENERATED_DIR}/main.h" "${GENERATED_DIR}/main_smc.txt"
        "${PROJECT_ROOT}/local/disc/DATA/sys/main.dol"
        "${RECOMPCORE}/module-template/gen_module_tables.py" VERBATIM)
endif()
if(POWERPROS_LLVM_DOL_DIR)
    if(NOT POWERPROS_ENABLE_REL)
        message(FATAL_ERROR "The LLVM DOL experiment uses the combined DOL/REL module tables")
    endif()
    file(GLOB CHUNKS CONFIGURE_DEPENDS "${GENERATED_DIR}/main_chunks/*.o")
    set_source_files_properties(${CHUNKS} PROPERTIES EXTERNAL_OBJECT TRUE GENERATED TRUE)
    list(APPEND CHUNKS llvm_support.c)
else()
    file(GLOB CHUNKS CONFIGURE_DEPENDS "${GENERATED_DIR}/main_chunks/*.c")
endif()
if(POWERPROS_LLVM_DOL_DIR)
    set(MODULE_EXPORT llvm_module_export.c)
else()
    set(MODULE_EXPORT module_export.c)
endif()
add_library(gRL8E54_recomp SHARED ${MODULE_EXPORT} "${TABLES}" ${CHUNKS}
    "${RECOMPCORE}/GXRuntime/src/core/cpu.c"
    "${RECOMPCORE}/GXRuntime/src/core/cpu_exception.c"
    "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter.c"
    "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_table.c"
    "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_float.c"
    "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_integer.c")
set_source_files_properties("${TABLES}" PROPERTIES GENERATED TRUE HEADER_FILE_ONLY TRUE)
target_include_directories(gRL8E54_recomp PRIVATE "${GENERATED_DIR}"
    "${RECOMPCORE}/GXRuntime/include"
    "${RECOMPCORE}/Source/Core/Core/PowerPC/StaticRecomp"
    "${CMAKE_CURRENT_BINARY_DIR}")
target_compile_definitions(gRL8E54_recomp PRIVATE DOLRECOMP_CPU_HEADER="core/cpu.h")
if(POWERPROS_ENABLE_REL)
    target_sources(gRL8E54_recomp PRIVATE ${REL_DISPATCH} ${REL_CHUNKS})
    if(POWERPROS_LLVM_REL_DIR)
        set_source_files_properties(llvm_rel_dispatch.c PROPERTIES COMPILE_DEFINITIONS
            "POWERPROS_REL_LOOKUP_BASE=${REL_LOOKUP_BASE}u;POWERPROS_REL_LOOKUP_SLOTS=${REL_LOOKUP_SLOTS}u")
    endif()
    target_include_directories(gRL8E54_recomp PRIVATE "${REL_GENERATED_DIR}")
    target_compile_definitions(gRL8E54_recomp PRIVATE POWERPROS_ENABLE_REL=1)
endif()
if(MSVC)
    if(POWERPROS_OPTIMIZE_MODULE)
        target_compile_options(gRL8E54_recomp PRIVATE /O2)
    else()
        target_compile_options(gRL8E54_recomp PRIVATE /Od)
    endif()
    target_compile_options(gRL8E54_recomp PRIVATE /bigobj /fp:strict /wd4102)
else()
    if(POWERPROS_OPTIMIZE_MODULE)
        target_compile_options(gRL8E54_recomp PRIVATE -O2)
    else()
        target_compile_options(gRL8E54_recomp PRIVATE -O0)
    endif()
    target_compile_options(gRL8E54_recomp PRIVATE -ffp-contract=off -fno-fast-math)
    target_link_libraries(gRL8E54_recomp PRIVATE m)
endif()
set_target_properties(gRL8E54_recomp PROPERTIES PREFIX "")
if(WIN32)
    add_executable(powerpros_startup_probe startup_probe.c
        "${RECOMPCORE}/GXRuntime/src/core/cpu.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_exception.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_table.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_float.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_integer.c")
    target_include_directories(powerpros_startup_probe PRIVATE
        "${RECOMPCORE}/GXRuntime/include"
        "${RECOMPCORE}/Source/Core/Core/PowerPC/StaticRecomp")
    target_link_libraries(powerpros_startup_probe PRIVATE gRL8E54_recomp)
    add_executable(powerpros_module_checks check_dispatch.c
        "${PROJECT_ROOT}/runtime/checks/native_memory.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_exception.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_table.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_float.c"
        "${RECOMPCORE}/GXRuntime/src/core/cpu_interpreter_integer.c")
    target_include_directories(powerpros_module_checks PRIVATE
        "${RECOMPCORE}/GXRuntime/include"
        "${RECOMPCORE}/Source/Core/Core/PowerPC/StaticRecomp")
    file(SHA256 "${PROJECT_ROOT}/local/disc/DATA/sys/main.dol" DOL_SHA256)
    target_compile_definitions(powerpros_module_checks PRIVATE
        DOLRECOMP_CPU_HEADER="core/cpu.h" DOL_SOURCE_SHA256="${DOL_SHA256}")
    target_link_libraries(powerpros_module_checks PRIVATE gRL8E54_recomp)
    enable_testing()
    add_test(NAME game_memory_through_module_abi COMMAND powerpros_module_checks
        "${PROJECT_ROOT}/local/analysis/memory-reference.bin")
    if(POWERPROS_ENABLE_REL)
        enable_language(CXX)
        add_executable(powerpros_rel_checks check_rel.c "${PROJECT_ROOT}/local/vendor/ModernGekko/src/runtime/module.cpp")
        target_include_directories(powerpros_rel_checks PRIVATE
            "${RECOMPCORE}/GXRuntime/include"
            "${PROJECT_ROOT}/local/vendor/ModernGekko/include"
            "${RECOMPCORE}/Source/Core/Core/PowerPC/StaticRecomp")
        target_link_libraries(powerpros_rel_checks PRIVATE gRL8E54_recomp bcrypt)
        if(POWERPROS_LLVM_DOL_DIR)
            file(GLOB LLVM_DOL_OBJECTS "${GENERATED_DIR}/main_chunks/*.o")
            list(LENGTH LLVM_DOL_OBJECTS LLVM_DOL_COUNT)
            list(LENGTH REL_CHUNKS REL_COUNT)
            math(EXPR EXPECTED_CHUNKS "${LLVM_DOL_COUNT} + ${REL_COUNT}")
            target_compile_definitions(powerpros_rel_checks PRIVATE POWERPROS_EXPECTED_CHUNKS=${EXPECTED_CHUNKS})
        endif()
        set(REL_PROBE "${PROJECT_ROOT}/local/analysis/boot-probe-20261008-005615-342/control/artifacts")
        add_test(NAME linked_rel_through_module_abi COMMAND powerpros_rel_checks
            "${PROJECT_ROOT}/local/analysis/rel-reference.bin"
            "${REL_PROBE}/mem1-low.bin" "${REL_PROBE}/mem1-high.bin")
    endif()
endif()
