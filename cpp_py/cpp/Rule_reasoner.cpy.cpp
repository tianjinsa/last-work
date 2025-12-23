#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <stack>
#include <string>
#include <algorithm>
#include <tuple>
using namespace std;
// 推理器类
class Rule_reasoner
{
private:
    struct line
    {
        vector<int> pres_id;
        int ans_id;
        line(const vector<int> &_pres_id, const int &_ans_id) : pres_id(_pres_id), ans_id(_ans_id) {}
    };

    struct node
    {
        // int data;
        vector<int> prelines_id, anslines_id;
    };
    vector<line> lines_list;                // 储存所有line
    vector<node> node_list;                 // 储存所有node
    unordered_map<string, int> name_id_map; // 根据name找node_id
    unordered_map<int, string> id_name_map; // 根据id找name
    unordered_set<int> known_set;           // 已知信息集合
    vector<int> reasoner_path;              // 推理路径，储存经过的line_id
    unordered_set<int> reasoner_set;        // 经过的line_id集合

    struct BackwardFrame
    {
        int u;
        int rule_idx;
    };
    stack<BackwardFrame> bw_stack;
    unordered_set<int> false_set;
    int in_backward = -1;

    // 辅助方法（仅内部使用）
    int get_line_id(const line &x);
    int get_name_id(const string &x);
    string get_id_name(const int &x);
    void add_rule(const vector<string> &pres, const string &ans);
    void add_rules(const vector<pair<vector<string>, string>> &rules);

public:
    Rule_reasoner() = default; // 构造后需通过 reset 提供规则

    // 添加已知信息
    void add_known(const vector<string> &known);
    // 清空已知信息
    void clear_known();
    // 开始推理，返回名字而非id
    pair<vector<string>, vector<int>> find();
    // 添加反例信息
    void add_false(const vector<string> &falses);
    // 清空反例信息
    void clear_false();
    // 返回: 状态 (0: 成功, 1: 失败, 2: 询问), 数据 (名字或名字列表), 路径 (规则id列表)
    tuple<int, vector<string>, vector<int>> step_backward(string target);

    // 重置推理器
    void reset(const vector<pair<vector<string>, string>> &rules)
    {
        lines_list.clear();
        node_list.clear();
        name_id_map.clear();
        id_name_map.clear();
        known_set.clear();
        reasoner_path.clear();
        false_set.clear();
        while (!bw_stack.empty())
            bw_stack.pop();
        in_backward = false;
        add_rules(rules);
    }
};
void Rule_reasoner::add_rule(const vector<string> &pres, const string &ans) // 添加规则
{
    vector<int> pres_id;
    for (const string &pre : pres)
    {
        pres_id.push_back(get_name_id(pre));
    }
    int ans_id = get_name_id(ans);
    line newline(pres_id, ans_id);
    int line_id = get_line_id(newline);
    for (const int &pre_id : pres_id)
    {
        node_list[pre_id].anslines_id.push_back(line_id);
    }
    node_list[ans_id].prelines_id.push_back(line_id);
}

void Rule_reasoner::add_rules(const vector<pair<vector<string>, string>> &rules) // 批量添加规则
{
    for (const auto &rule : rules)
    {
        add_rule(rule.first, rule.second);
    }
}

void Rule_reasoner::add_known(const vector<string> &known) // 添加已知信息
{
    for (const string &k : known)
    {
        known_set.insert(get_name_id(k));
    }
}

void Rule_reasoner::clear_known() // 清空已知信息
{
    known_set.clear();
    reasoner_path.clear();
}

int Rule_reasoner::get_line_id(const line &x) // 插入line并获得id
{
    lines_list.push_back(x);
    return static_cast<int>(lines_list.size()) - 1;
}

int Rule_reasoner::get_name_id(const string &x) // 插入name并获得id
{
    auto it = name_id_map.find(x);
    if (it == name_id_map.end())
    {
        int id = static_cast<int>(name_id_map.size());
        name_id_map[x] = id;
        id_name_map[id] = x;
        node_list.push_back(node());
        return id;
    }
    else
    {
        return it->second;
    }
}

string Rule_reasoner::get_id_name(const int &x) // 根据id找name
{
    return id_name_map[x];
}

pair<vector<string>, vector<int>> Rule_reasoner::find() // 开始推理
{
    vector<string> result;
    reasoner_path.clear();
    stack<int> s;
    for (const int &id : known_set)
    {
        s.push(id);
    }
    while (!s.empty())
    {
        int now_id = s.top();
        s.pop();
        node &now_node = node_list[now_id];
        if (now_node.anslines_id.empty()) // 推理到尽头
        {
            result.push_back(get_id_name(now_id));
            continue;
        }
        for (const int &line_id : now_node.anslines_id)
        {
            line &now_line = lines_list[line_id];
            if (known_set.count(now_line.ans_id))
                continue; // 已经知道的就不推理了
            bool can_get = true;
            for (const int &pre_id : now_line.pres_id)
            {
                if (!known_set.count(pre_id))
                {
                    can_get = false;
                    break;
                }
            }
            if (can_get)
            {
                reasoner_path.push_back(line_id);
                known_set.insert(now_line.ans_id);
                s.push(now_line.ans_id);
            }
        }
    }

    return {result, reasoner_path};
}

void Rule_reasoner::add_false(const vector<string> &falses)
{
    for (const string &f : falses)
    {
        false_set.insert(get_name_id(f));
    }
}

void Rule_reasoner::clear_false()
{
    false_set.clear();
}

tuple<int, vector<string>, vector<int>> Rule_reasoner::step_backward(string target_name)
{
    int target_id = get_name_id(target_name);
    reasoner_path.clear();
    reasoner_set.clear();

    if (in_backward != target_id)
    {
        while (!bw_stack.empty())
            bw_stack.pop();
        bw_stack.push({target_id, 0});
        in_backward = target_id;
    }

    while (!bw_stack.empty())
    {
        BackwardFrame &top = bw_stack.top();
        int u = top.u;

        if (known_set.count(u))
        {
            bw_stack.pop();
            continue;
        }
        if (false_set.count(u))
        {
            bw_stack.pop();
            continue;
        }

        vector<int> &rules = node_list[u].prelines_id;

        if (top.rule_idx >= (int)(rules.size()))
        {
            false_set.insert(u);
            bw_stack.pop();
            continue;
        }

        int line_id = rules[top.rule_idx];
        line &l = lines_list[line_id];

        bool rule_possible = true;
        int subgoal = -1;
        vector<string> to_ask;

        for (const int &pre_id : l.pres_id)
        {
            if (false_set.count(pre_id))
            {
                rule_possible = false;
                break;
            }
            if (known_set.count(pre_id))
                continue;

            if (node_list[pre_id].prelines_id.empty())
            {
                to_ask.push_back(get_id_name(pre_id));
            }
            else
            {
                if (subgoal == -1)
                    subgoal = pre_id;
            }
        }

        if (!rule_possible)
        {
            top.rule_idx++;
            continue;
        }

        if (subgoal != -1)
        {
            bw_stack.push({subgoal, 0});
            continue;
        }

        if (!to_ask.empty())
        {
            return {2, to_ask, reasoner_path};
        }

        known_set.insert(u);
        if (reasoner_set.count(line_id) == 0)
        {
            reasoner_path.push_back(line_id);
            reasoner_set.insert(line_id);
        }
        bw_stack.pop();
    }

    in_backward = -1;
    if (known_set.count(target_id))
        return {0, {target_name}, reasoner_path};
    return {1, {}, reasoner_path};
}
