#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "../cpp/Rule_reasoner.cpy.cpp"

namespace py = pybind11;

PYBIND11_MODULE(Rule_reasoner, m)
{

    auto cls_Rule_reasoner = py::class_<Rule_reasoner>(m, "Rule_reasoner", R"PYBIND_DOC(推理器类)PYBIND_DOC");
    cls_Rule_reasoner.def(py::init<>(), R"PYBIND_DOC(构造后需通过 reset 提供规则)PYBIND_DOC");
    cls_Rule_reasoner.def("add_known", &Rule_reasoner::add_known, py::arg("known"), R"PYBIND_DOC(添加已知信息)PYBIND_DOC");
    cls_Rule_reasoner.def("clear_known", &Rule_reasoner::clear_known, R"PYBIND_DOC(清空已知信息)PYBIND_DOC");
    cls_Rule_reasoner.def("find", &Rule_reasoner::find, R"PYBIND_DOC(开始推理，返回名字而非id)PYBIND_DOC");
    cls_Rule_reasoner.def("add_false", &Rule_reasoner::add_false, py::arg("falses"), R"PYBIND_DOC(添加反例信息)PYBIND_DOC");
    cls_Rule_reasoner.def("clear_false", &Rule_reasoner::clear_false, R"PYBIND_DOC(清空反例信息)PYBIND_DOC");
    cls_Rule_reasoner.def("step_backward", &Rule_reasoner::step_backward, py::arg("target"), R"PYBIND_DOC(返回: 状态 (0: 成功, 1: 失败, 2: 询问), 数据 (名字或名字列表), 路径 (规则id列表))PYBIND_DOC");
    cls_Rule_reasoner.def("reset", &Rule_reasoner::reset, py::arg("rules"), R"PYBIND_DOC(重置推理器)PYBIND_DOC");
}
