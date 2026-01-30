# EmailJS 反馈功能配置教程

本教程将指导你如何配置 EmailJS，以便“问题反馈”功能可以发送邮件到你的邮箱。

## 第一步：注册并配置 EmailJS 账号

1.  访问 [EmailJS 官网](https://www.emailjs.com/) 并注册一个免费账号。
2.  登录 Dashboard。

## 第二步：添加邮件服务 (Email Service)

这是用来发送邮件的实际服务（如 Gmail）。

1.  点击左侧菜单的 **"Email Services"**。
2.  点击 **"Add New Service"**。
3.  选择 **"Gmail"** (或其他你使用的服务)。
4.  点击 **"Connect Account"** 并授权你的邮箱。
5.  **重要**：创建成功后，你会看到一个 `Service ID`（例如 `service_z4x9q2a`）。
    *   👉 **请记录下这个 ID**。

## 第三步：创建邮件模板 (Email Template)

这是邮件内容的格式。

1.  点击左侧菜单的 **"Email Templates"**。
2.  点击 **"Create New Template"**。
3.  在 **"Subject"** (邮件标题) 中填写：`用户反馈 - {{problem_type}}`
4.  在 **"Content"** (邮件正文) 中，复制并粘贴以下 HTML 代码：

```html
<div style="font-family: sans-serif; padding: 20px; border: 1px solid #eee; border-radius: 5px;">
    <h2 style="color: #4f46e5;">用户反馈报告</h2>
    
    <p><strong>问题类型:</strong> {{problem_type}}</p>
    
    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
    
    <h3 style="margin-bottom: 10px;">规范信息</h3>
    <table style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 8px; background: #f8fafc; width: 120px;"><strong>规范名称:</strong></td>
            <td style="padding: 8px;">{{identified_name}}</td>
        </tr>
        <tr>
            <td style="padding: 8px; background: #f8fafc;"><strong>规范编号:</strong></td>
            <td style="padding: 8px;">{{identified_code}}</td>
        </tr>
    </table>
    
    <h3 style="margin-bottom: 10px;">详细描述</h3>
    <div style="background: #fdf2f8; padding: 15px; border-radius: 4px; border-left: 4px solid #db2777;">
        {{description}}
    </div>
    
    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
    
    <p style="color: #888; font-size: 12px;">
        User Agent: {{user_agent}}
    </p>
</div>
```

5.  点击上方的 **"To Email"** 选项卡，确保它设置为你希望接收通知的邮箱。
6.  点击 **"Save"** 保存。
7.  **重要**：保存后，查看 Settings 选项卡，你会看到一个 `Template ID`（例如 `template_8a2b3c`）。
    *   👉 **请记录下这个 ID**。

## 第四步：获取公钥 (Public Key)

1.  点击左侧菜单的 **"Account"** (或者点击右上角头像 -> Account)。
2.  找到 **"API Keys"** 部分。
3.  复制 **"Public Key"** (通常是一串随机字符，如 `user_XyZ123...` 或 `p_abc123...`)。
    *   👉 **请记录下这个 Key**。

---

## 第五步：项目配置 (Vercel 部署)

如果你已将项目部署到 Vercel，请按照以下步骤配置环境变量：

1.  登录 Vercel Dashboard，进入你的项目。
2.  点击顶部菜单的 **"Settings"** -> **"Environment Variables"**。
3.  添加以下三个变量（使用你之前记录的值）：

| Key (变量名) | Value (你的值) |
| :--- | :--- |
| `VITE_EMAILJS_SERVICE_ID` | `service_xxxxxx` (你的 Service ID) |
| `VITE_EMAILJS_TEMPLATE_ID` | `template_xxxxxx` (你的 Template ID) |
| `VITE_EMAILJS_PUBLIC_KEY` | `xxxx-xxxx-xxxx` (你的 Public Key) |

4.  保存后，你需要 **重新部署 (Redeploy)** 项目才能生效。
    *   去 "Deployments" 页面，点击最新的部署右侧的三点 -> "Redeploy"。

---

## 第六步：本地开发配置 (可选)

如果你想在本地 (`localhost`) 测试发送邮件：

1.  在项目 `frontend` 目录下，新建一个名为 `.env.local` 的文件。
2.  填入以下内容：

```bash
VITE_EMAILJS_SERVICE_ID=你的Service_ID
VITE_EMAILJS_TEMPLATE_ID=你的Template_ID
VITE_EMAILJS_PUBLIC_KEY=你的Public_Key
```

3.  重启前端服务：
    ```bash
    npm run dev
    ```

## 测试

配置完成后：
1. 打开网页，点击表格右侧的 "反馈"。
2. 填写测试内容并提交。
3. 如果配置正确，你会看到“反馈已发送”的提示，并且你的邮箱会收到一封格式精美的邮件。
