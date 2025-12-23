# 1. 建议将 CMake 最低版本提升到 3.15 以上
# (FindPython3 模块在 3.12 引入，3.15 更稳定)
cmake_minimum_required(VERSION 3.15)

project(last-work)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ------------------------------------------------------------
# 用户可配置路径（默认值按需求指定）
# ------------------------------------------------------------
set(CPP_PY_SOURCE_DIR "${CMAKE_SOURCE_DIR}/cpp_py/cpp" CACHE PATH "存放 .cpy.cpp/.cpp 原始文件的目录")
set(CPP_PY_BCPP_DIR   "${CMAKE_SOURCE_DIR}/cpp_py/bcpp" CACHE PATH "自动生成 *.bcpy.cpp 的目录")
set(CPP_PY_OUTPUT_DIR "${CMAKE_SOURCE_DIR}" CACHE PATH "存放生成 .pyd/.pyi 的目录")

# 兼容旧变量名
set(OUTPUT_DIR "${CPP_PY_OUTPUT_DIR}" CACHE STRING "输出目录，用于存放生成的 .pyd 和 .pyi 文件")

# ------------------------------------------------------------
# 选择 Python 解释器：优先使用工作区 .venv
# ------------------------------------------------------------
set(_VENV_PY "${CMAKE_SOURCE_DIR}/.venv/Scripts/python.exe")
if(NOT EXISTS "${_VENV_PY}")
    # POSIX 兼容路径
    set(_VENV_PY "${CMAKE_SOURCE_DIR}/.venv/bin/python")
endif()

if(EXISTS "${_VENV_PY}")
    set(Python3_EXECUTABLE "${_VENV_PY}" CACHE FILEPATH "Python executable" FORCE)
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
else()
    find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
endif()

# ------------------------------------------------------------
# pybind11：用户可指定根目录；否则尝试 .extern/pybind11，再回退到 find_package
# ------------------------------------------------------------
set(PYBIND11_ROOT "" CACHE PATH "pybind11 安装根目录（可选）")

if(PYBIND11_ROOT)
    find_package(pybind11 CONFIG REQUIRED PATHS "${PYBIND11_ROOT}" NO_DEFAULT_PATH)
elseif(EXISTS "${CMAKE_SOURCE_DIR}/.extern/pybind11/CMakeLists.txt")
    add_subdirectory(.extern/pybind11)
else()
    find_package(pybind11 CONFIG REQUIRED)
endif()

# ------------------------------------------------------------
# 配置阶段：调用 Python 脚本生成 *.bcpy.cpp
# ------------------------------------------------------------
file(MAKE_DIRECTORY "${CPP_PY_BCPP_DIR}")
execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/.cmakepy/generate_bcpy.py"
            --source "${CPP_PY_SOURCE_DIR}" --bcpp "${CPP_PY_BCPP_DIR}" --out "${CPP_PY_OUTPUT_DIR}"
    WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    RESULT_VARIABLE _GEN_BCPP_RES
)
if(NOT _GEN_BCPP_RES EQUAL 0)
    message(FATAL_ERROR "generate_bcpy.py 运行失败，返回值：${_GEN_BCPP_RES}")
endif()

# ------------------------------------------------------------
# 扫描生成的 *.bcpy.cpp 并为每个创建 pybind11 模块
# ------------------------------------------------------------
file(GLOB_RECURSE BCPP_FILES CONFIGURE_DEPENDS "${CPP_PY_BCPP_DIR}/*.bcpy.cpp")

if(NOT BCPP_FILES)
    message(STATUS "未找到任何 *.bcpy.cpp（源目录：${CPP_PY_SOURCE_DIR}）")
else()
    foreach(_file IN LISTS BCPP_FILES)
        # 计算相对路径和模块名
        file(RELATIVE_PATH _rel "${CPP_PY_BCPP_DIR}" "${_file}")
        get_filename_component(_mod_basename "${_file}" NAME_WE) # 去掉 .cpp
        string(REPLACE ".bcpy" "" _modname "${_mod_basename}")

        if(_modname STREQUAL "")
            message(WARNING "跳过文件，名称格式异常: ${_file}")
            continue()
        endif()

        # 目标名使用模块名，保持与 PYBIND11_MODULE 一致
        set(_target "${_modname}")

        if(TARGET "${_target}")
            message(WARNING "模块目标 ${_target} 已存在，跳过 ${_file}")
            continue()
        endif()

        pybind11_add_module(${_target} ${_file})

        # 输出目录按子目录结构放置
        get_filename_component(_file_dir "${_file}" DIRECTORY)
        file(RELATIVE_PATH _rel_dir "${CPP_PY_BCPP_DIR}" "${_file_dir}")
        if(_rel_dir STREQUAL "")
            set(_rel_dir ".")
        endif()

        set(_out_dir "${CPP_PY_OUTPUT_DIR}/${_rel_dir}")
        file(TO_NATIVE_PATH "${_out_dir}" _out_dir_native)
        set_target_properties(${_target} PROPERTIES
            LIBRARY_OUTPUT_DIRECTORY "${_out_dir_native}"
            RUNTIME_OUTPUT_DIRECTORY "${_out_dir_native}"
            ARCHIVE_OUTPUT_DIRECTORY "${_out_dir_native}"
        )

        # 针对 MinGW 启用静态链接选项
        if(MINGW)
            target_link_options(${_target} PRIVATE
                "-static-libgcc"
                "-static-libstdc++"
                "-Wl,-Bstatic,--whole-archive" "-lwinpthread" "-Wl,--no-whole-archive"
            )
        endif()

        # 计算包名（用于 stubgen 导入）
        if(_rel_dir STREQUAL ".")
            set(_pkg_prefix "")
        else()
            string(REPLACE "\\" "." _pkg_prefix "${_rel_dir}")
            string(REPLACE "/" "." _pkg_prefix "${_pkg_prefix}")
        endif()

        if(_pkg_prefix STREQUAL "")
            set(_module_import "${_modname}")
        else()
            set(_module_import "${_pkg_prefix}.${_modname}")
        endif()

        # 为包目录生成 __init__.py（仅限子目录），并生成 .pyi，清理 __pycache__
        add_custom_command(
            TARGET ${_target}
            POST_BUILD
            COMMAND "${CMAKE_COMMAND}" -E make_directory "${_out_dir_native}"
            COMMAND "${Python3_EXECUTABLE}" -c "from pathlib import Path; base=Path(r'${CPP_PY_OUTPUT_DIR}'); rel=Path(r'${_rel_dir}'); [ (base.joinpath(*rel.parts[:i+1]).mkdir(parents=True, exist_ok=True), (base.joinpath(*rel.parts[:i+1])/'__init__.py').touch()) for i in range(len(rel.parts)) ]"
            COMMAND "${CMAKE_COMMAND}" -E env "PYTHONPATH=${CPP_PY_OUTPUT_DIR}"
                    "${Python3_EXECUTABLE}" -m pybind11_stubgen "${_module_import}"
                    --output-dir "${CPP_PY_OUTPUT_DIR}"
            WORKING_DIRECTORY "${CPP_PY_OUTPUT_DIR}"
            COMMAND "${Python3_EXECUTABLE}" -c "from pathlib import Path; root=Path(r'${CPP_PY_OUTPUT_DIR}'); [p.unlink() for p in root.rglob('__pycache__/*') if p.is_file()]; [p.rmdir() for p in sorted(root.rglob('__pycache__'), key=lambda x: len(str(x)), reverse=True) if p.exists()]"
            COMMAND "${Python3_EXECUTABLE}" "${CMAKE_SOURCE_DIR}/.cmakepy/postprocess_pyi.py" --root "${CPP_PY_OUTPUT_DIR}"
            COMMENT "生成 ${_module_import}.pyi，写入 __init__.py，清理 __pycache__，并后处理 pyi"
        )
    endforeach()
endif()
