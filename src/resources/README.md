# Resources 文件夹

这个文件夹用于存放项目的资源文件，包括：

## 数据文件
- `seen_event_ids.json` - 存储已查看的事件ID列表
- 其他JSON配置文件

## 使用说明
- 所有资源文件都应该放在这个文件夹中
- 避免在代码中硬编码配置信息
- 使用相对路径引用这些资源文件

## 文件结构
```
src/resources/
├── README.md
├── seen_event_ids.json
└── (其他资源文件)
```
