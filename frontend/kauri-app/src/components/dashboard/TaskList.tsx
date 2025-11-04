import React from 'react';
import { AlertCircle, Clock, CheckCircle } from 'lucide-react';
import { Task } from '../../types';

interface TaskListProps {
  tasks: Task[];
}

const TaskList: React.FC<TaskListProps> = ({ tasks }) => {
  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return <AlertCircle size={18} className="text-red-600" />;
      case 'moyen':
        return <Clock size={18} className="text-yellow-600" />;
      default:
        return <CheckCircle size={18} className="text-gray-400" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'text-red-600 bg-red-50';
      case 'moyen':
        return 'text-yellow-600 bg-yellow-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100">
      <div className="p-6 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">À faire</h2>
      </div>
      <div className="divide-y divide-gray-100">
        {tasks.map((task) => (
          <div key={task.id} className="p-6 hover:bg-gray-50 transition">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${getPriorityColor(task.priority)}`}>
                  {getPriorityIcon(task.priority)}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{task.title}</p>
                  {task.urgentCount && (
                    <p className="text-sm text-red-600 mt-1">
                      {task.urgentCount} {task.urgentCount > 1 ? 'urgentes' : 'urgente'}
                    </p>
                  )}
                </div>
              </div>
              <span className={`px-3 py-1 text-xs font-medium rounded-full ${getPriorityColor(task.priority)}`}>
                {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TaskList;
