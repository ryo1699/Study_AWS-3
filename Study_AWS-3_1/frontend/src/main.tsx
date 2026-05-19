import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { ImageUp, RefreshCw, Save, Trash2 } from "lucide-react";
import "./styles.css";

type TaskStatus = "pending" | "in_progress" | "done";

type Task = {
  id: number;
  title: string;
  description?: string | null;
  status: TaskStatus;
  pictureS3Key?: string | null;
  pictureUrl?: string | null;
  createdAt: string;
  updatedAt: string;
};

const statusLabels: Record<TaskStatus, string> = {
  pending: "Pending",
  in_progress: "In progress",
  done: "Done"
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<TaskStatus>("pending");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<number | "">("");
  const [imageUrls, setImageUrls] = useState<Record<number, string>>({});
  const [message, setMessage] = useState("");

  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId),
    [selectedTaskId, tasks]
  );

  async function loadTasks() {
    const nextTasks = await request<Task[]>("/api/tasks");
    setTasks(nextTasks);
    if (!selectedTaskId && nextTasks.length > 0) setSelectedTaskId(nextTasks[0].id);
  }

  useEffect(() => {
    loadTasks().catch((error) => setMessage(error.message));
  }, []);

  async function createTask(event: React.FormEvent) {
    event.preventDefault();
    const task = await request<Task>("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ title, description, status })
    });
    setTitle("");
    setDescription("");
    setStatus("pending");
    setSelectedTaskId(task.id);
    setMessage(`Task #${task.id} created`);
    await loadTasks();
  }

  async function uploadImage() {
    if (!selectedTask || !selectedFile) return;
    const upload = await request<{ uploadUrl: string; s3Key: string }>("/api/tasks/" + selectedTask.id + "/image-upload-url", {
      method: "POST",
      body: JSON.stringify({ filename: selectedFile.name, contentType: selectedFile.type || "image/jpeg" })
    });
    const putResponse = await fetch(upload.uploadUrl, {
      method: "PUT",
      headers: {
        "Content-Type": selectedFile.type || "image/jpeg",
        "x-amz-server-side-encryption": "AES256"
      },
      body: selectedFile
    });
    if (!putResponse.ok) throw new Error(`S3 upload failed: ${putResponse.status}`);
    setSelectedFile(null);
    setMessage(`Image uploaded for task #${selectedTask.id}`);
    await loadTasks();
  }

  async function loadImage(task: Task) {
    const response = await request<{ pictureUrl: string }>("/api/tasks/" + task.id + "/image-view-url", {
      method: "POST",
      body: JSON.stringify({})
    });
    setImageUrls((current) => ({ ...current, [task.id]: response.pictureUrl }));
  }

  async function deleteTask(task: Task) {
    await request<void>("/api/tasks/" + task.id, { method: "DELETE" });
    setMessage(`Task #${task.id} deleted`);
    await loadTasks();
  }

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <h1>Study AWS 3 Tasks</h1>
          <p>Private S3 upload and CloudFront signed image viewing</p>
        </div>
        <button className="icon-button" onClick={loadTasks} aria-label="Reload tasks" title="Reload tasks">
          <RefreshCw size={18} />
        </button>
      </section>

      <section className="grid">
        <form className="panel" onSubmit={createTask}>
          <h2>Register</h2>
          <label>
            Title
            <input value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={255} />
          </label>
          <label>
            Description
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} />
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as TaskStatus)}>
              {Object.entries(statusLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <button className="primary" type="submit">
            <Save size={18} />
            Save task
          </button>
        </form>

        <section className="panel">
          <h2>Image upload</h2>
          <label>
            Task
            <select value={selectedTaskId} onChange={(event) => setSelectedTaskId(Number(event.target.value))}>
              {tasks.map((task) => (
                <option key={task.id} value={task.id}>#{task.id} {task.title}</option>
              ))}
            </select>
          </label>
          <label>
            Image
            <input type="file" accept="image/*" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} />
          </label>
          <button className="primary" type="button" disabled={!selectedTask || !selectedFile} onClick={() => uploadImage().catch((error) => setMessage(error.message))}>
            <ImageUp size={18} />
            Upload image
          </button>
        </section>
      </section>

      {message && <p className="notice">{message}</p>}

      <section className="task-list">
        {tasks.map((task) => (
          <article key={task.id} className="task-card">
            <div className="task-card__main">
              <span className={"status status--" + task.status}>{statusLabels[task.status]}</span>
              <h3>{task.title}</h3>
              <p>{task.description || "No description"}</p>
              <small>#{task.id} / updated {new Date(task.updatedAt).toLocaleString()}</small>
            </div>
            <div className="task-card__actions">
              {task.pictureS3Key && (
                <button type="button" onClick={() => loadImage(task).catch((error) => setMessage(error.message))}>
                  View image
                </button>
              )}
              <button className="danger" type="button" onClick={() => deleteTask(task).catch((error) => setMessage(error.message))} aria-label="Delete task" title="Delete task">
                <Trash2 size={18} />
              </button>
            </div>
            {imageUrls[task.id] && <img className="preview" src={imageUrls[task.id]} alt={task.title} />}
          </article>
        ))}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);

