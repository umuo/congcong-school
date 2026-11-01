"""镜像 core jump.ts 的抽样；种子由服务端生成，固定后不随修订变化。"""

MASK = (1 << 64) - 1


def djb2(value):
    state = 5381
    for byte in value.encode():
        state = (state * 33 + byte) & MASK
    return state


def mix64(value):
    value = (value + 0x9E3779B97F4A7C15) & MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK
    return value ^ (value >> 31)


def shuffled(values, seed):
    result = list(values)
    state = djb2(seed)
    for i in range(len(result) - 1, 0, -1):
        state = (state + 1) & MASK
        j = int(((mix64(state) >> 11) / 2**53) * (i + 1))
        result[i], result[j] = result[j], result[i]
    return result


def sample_jump(sources, seed, size=15):
    groups = [
        shuffled(source["question_refs"], f"{seed}#{source['lesson_id']}")
        for source in sources
        if source["question_refs"]
    ]
    groups = shuffled(groups, f"{seed}#groups")
    picked, round_index = [], 0
    target = min(size, sum(map(len, groups)))
    while len(picked) < target:
        for group in groups:
            if round_index < len(group) and len(picked) < target:
                picked.append(group[round_index])
        round_index += 1
    return shuffled(picked, f"{seed}#order")
