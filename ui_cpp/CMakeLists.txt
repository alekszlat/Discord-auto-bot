# CMake configuration for DiscordConfigEditor
# This CMakeLists.txt sets up the build for a C++17 wxWidgets GUI

# 1. Specify minimum CMake version and project name/language
cmake_minimum_required(VERSION 3.14)
project(DiscordConfigEditor LANGUAGES CXX)

# 2. Enforce C++17 standard
#    Ensures all targets compile with at least C++17 features
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 3. Locate wxWidgets
#    - Searches for core and base components (for basic GUI)
#    - If not found, errors out reminding to install the dev package
find_package(wxWidgets REQUIRED COMPONENTS core base)
if(NOT wxWidgets_FOUND)
    message(FATAL_ERROR "wxWidgets not found. Install libwxgtk3.2-dev.")
endif()
#    - Include wxWidgets build settings (compiler flags, etc.)
include(${wxWidgets_USE_FILE})

# 4. Locate nlohmann_json (header-only JSON library)
#    - First tries to find CMake package configuration
#    - If that fails, falls back to checking for the header under /usr/include
find_package(nlohmann_json 3.2.0 QUIET)
if(NOT TARGET nlohmann_json::nlohmann_json)
    # Try alternative include path lookup
    find_path(NLOHMANN_JSON_INCLUDE_DIR nlohmann/json.hpp PATHS /usr/include)
    if(NOT NLOHMANN_JSON_INCLUDE_DIR)
        message(FATAL_ERROR "nlohmann/json.hpp not found. Install nlohmann-json3-dev or add its include path.")
    endif()
    set(NLOHMANN_JSON_INCLUDE_DIRS ${NLOHMANN_JSON_INCLUDE_DIR})
endif()

# 5. List all source files for the executable
#    Add additional .cpp/.h files here as your project grows
set(SOURCES
    main.cpp
)

# 6. Define the executable target
#    - ${PROJECT_NAME} will be replaced with 'DiscordConfigEditor'
add_executable(${PROJECT_NAME} ${SOURCES})

# 7. Specify include directories for the target
#    - wxWidgets include paths (for GUI headers)
#    - nlohmann_json include path if header-only fallback is used
#    The generator expression checks if the imported target exists
#    and picks the correct include directories accordingly
target_include_directories(${PROJECT_NAME}
    PRIVATE
        ${wxWidgets_INCLUDE_DIRS}
        $<IF:$<TARGET_EXISTS:nlohmann_json::nlohmann_json>,"\
"<TARGET_PROPERTY:nlohmann_json::nlohmann_json,INTERFACE_INCLUDE_DIRECTORIES>,"\
"${NLOHMANN_JSON_INCLUDE_DIRS}>
)

# 8. Link libraries to the executable
#    - Links against wxWidgets core/base libraries for GUI support
#    - Links against nlohmann_json target if available (no-op if header-only fallback)
target_link_libraries(${PROJECT_NAME}
    PRIVATE
        ${wxWidgets_LIBRARIES}
        $<IF:$<TARGET_EXISTS:nlohmann_json::nlohmann_json>,nlohmann_json::nlohmann_json,>
)

# 9. (Optional) Specify output directory for the built binary
#    - Places the executable under build/bin for easy access
set_target_properties(${PROJECT_NAME} PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)