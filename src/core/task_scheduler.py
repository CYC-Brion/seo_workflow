"""
任务调度器
基于APScheduler的任务调度系统
"""

import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from src.utils import get_logger, exception_handler


class TaskScheduler:
    """任务调度器"""

    def __init__(
        self,
        max_workers: int = 10,
        jobstore: str = "memory",
        timezone: str = "UTC"
    ):
        """
        初始化任务调度器

        Args:
            max_workers: 最大工作线程数
            jobstore: 任务存储类型（目前只支持memory）
            timezone: 时区
        """
        self.max_workers = max_workers
        self.timezone = timezone
        self.logger = get_logger("task_scheduler")
        self.exception_handler = exception_handler

        # 初始化调度器
        self._init_scheduler()

        # 任务锁和状态
        self.lock = Lock()
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.task_history: List[Dict[str, Any]] = []

        self.logger.info(
            f"任务调度器初始化",
            max_workers=max_workers,
            timezone=timezone
        )

    def _init_scheduler(self) -> None:
        """初始化APScheduler"""
        jobstores = {
            'default': MemoryJobStore()
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=self.max_workers)
        }

        job_defaults = {
            'coalesce': True,  # 合并错过执行的作业
            'max_instances': 3,  # 最大并发实例数
            'misfire_grace_time': 30  # 错过执行的宽限时间（秒）
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=self.timezone
        )

    def start(self) -> bool:
        """启动调度器"""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                self.logger.info("任务调度器已启动")
                return True
            else:
                self.logger.warning("任务调度器已经在运行")
                return False
        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "start_scheduler"},
                reraise=False
            )
            return False

    def stop(self, wait: bool = True) -> bool:
        """停止调度器

        Args:
            wait: 是否等待正在执行的任务完成

        Returns:
            是否成功停止
        """
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=wait)
                self.logger.info(f"任务调度器已停止，等待任务完成: {wait}")
                return True
            else:
                self.logger.warning("任务调度器未运行")
                return False
        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "stop_scheduler", "wait": wait},
                reraise=False
            )
            return False

    def add_interval_job(
        self,
        func: Callable,
        interval_seconds: int,
        job_id: Optional[str] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **job_kwargs
    ) -> Optional[str]:
        """添加间隔任务

        Args:
            func: 要执行的函数
            interval_seconds: 间隔秒数
            job_id: 任务ID，如果为None则自动生成
            args: 函数位置参数
            kwargs: 函数关键字参数
            start_date: 开始时间
            end_date: 结束时间
            **job_kwargs: 其他APScheduler作业参数

        Returns:
            任务ID，如果添加失败返回None
        """
        try:
            job_id = job_id or f"interval_{int(time.time())}_{func.__name__}"

            trigger = IntervalTrigger(seconds=interval_seconds)

            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                start_date=start_date,
                end_date=end_date,
                **job_kwargs
            )

            with self.lock:
                self.jobs[job_id] = {
                    "job_id": job_id,
                    "type": "interval",
                    "func": func.__name__,
                    "interval_seconds": interval_seconds,
                    "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "added_time": datetime.now().isoformat(),
                }

            self.logger.info(
                f"添加间隔任务: {job_id}",
                interval_seconds=interval_seconds,
                func_name=func.__name__
            )

            return job_id

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "add_interval_job",
                    "job_id": job_id,
                    "interval_seconds": interval_seconds,
                    "func": func.__name__
                },
                reraise=False
            )
            return None

    def add_cron_job(
        self,
        func: Callable,
        cron_expression: str,
        job_id: Optional[str] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **job_kwargs
    ) -> Optional[str]:
        """添加Cron任务

        Args:
            func: 要执行的函数
            cron_expression: Cron表达式，如 "0 2 * * *" 表示每天凌晨2点
            job_id: 任务ID，如果为None则自动生成
            args: 函数位置参数
            kwargs: 函数关键字参数
            start_date: 开始时间
            end_date: 结束时间
            **job_kwargs: 其他APScheduler作业参数

        Returns:
            任务ID，如果添加失败返回None
        """
        try:
            job_id = job_id or f"cron_{int(time.time())}_{func.__name__}"

            # 解析Cron表达式
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"无效的Cron表达式: {cron_expression}，需要5个部分")

            minute, hour, day, month, day_of_week = parts

            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                start_date=start_date,
                end_date=end_date
            )

            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                **job_kwargs
            )

            with self.lock:
                self.jobs[job_id] = {
                    "job_id": job_id,
                    "type": "cron",
                    "func": func.__name__,
                    "cron_expression": cron_expression,
                    "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "added_time": datetime.now().isoformat(),
                }

            self.logger.info(
                f"添加Cron任务: {job_id}",
                cron_expression=cron_expression,
                func_name=func.__name__
            )

            return job_id

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "add_cron_job",
                    "job_id": job_id,
                    "cron_expression": cron_expression,
                    "func": func.__name__
                },
                reraise=False
            )
            return None

    def add_one_time_job(
        self,
        func: Callable,
        run_time: datetime,
        job_id: Optional[str] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        **job_kwargs
    ) -> Optional[str]:
        """添加一次性任务

        Args:
            func: 要执行的函数
            run_time: 运行时间
            job_id: 任务ID，如果为None则自动生成
            args: 函数位置参数
            kwargs: 函数关键字参数
            **job_kwargs: 其他APScheduler作业参数

        Returns:
            任务ID，如果添加失败返回None
        """
        try:
            job_id = job_id or f"onetime_{int(time.time())}_{func.__name__}"

            trigger = DateTrigger(run_date=run_time)

            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                **job_kwargs
            )

            with self.lock:
                self.jobs[job_id] = {
                    "job_id": job_id,
                    "type": "one_time",
                    "func": func.__name__,
                    "run_time": run_time.isoformat(),
                    "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                    "added_time": datetime.now().isoformat(),
                }

            self.logger.info(
                f"添加一次性任务: {job_id}",
                run_time=run_time.isoformat(),
                func_name=func.__name__
            )

            return job_id

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "add_one_time_job",
                    "job_id": job_id,
                    "run_time": run_time.isoformat(),
                    "func": func.__name__
                },
                reraise=False
            )
            return None

    def remove_job(self, job_id: str) -> bool:
        """移除任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功移除
        """
        try:
            success = self.scheduler.remove_job(job_id)

            with self.lock:
                if job_id in self.jobs:
                    del self.jobs[job_id]

            self.logger.info(f"移除任务: {job_id}", success=success)
            return success

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "remove_job", "job_id": job_id},
                reraise=False
            )
            return False

    def pause_job(self, job_id: str) -> bool:
        """暂停任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功暂停
        """
        try:
            self.scheduler.pause_job(job_id)

            with self.lock:
                if job_id in self.jobs:
                    self.jobs[job_id]["paused"] = True
                    self.jobs[job_id]["paused_time"] = datetime.now().isoformat()

            self.logger.info(f"暂停任务: {job_id}")
            return True

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "pause_job", "job_id": job_id},
                reraise=False
            )
            return False

    def resume_job(self, job_id: str) -> bool:
        """恢复任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功恢复
        """
        try:
            self.scheduler.resume_job(job_id)

            with self.lock:
                if job_id in self.jobs:
                    self.jobs[job_id]["paused"] = False
                    self.jobs[job_id]["resumed_time"] = datetime.now().isoformat()

            self.logger.info(f"恢复任务: {job_id}")
            return True

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "resume_job", "job_id": job_id},
                reraise=False
            )
            return False

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息

        Args:
            job_id: 任务ID

        Returns:
            任务信息字典
        """
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return None

            with self.lock:
                job_info = self.jobs.get(job_id, {}).copy()

            job_info.update({
                "job_id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
                "pending": job.pending,
            })

            return job_info

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "get_job", "job_id": job_id},
                reraise=False
            )
            return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务

        Returns:
            任务列表
        """
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                job_info = self.get_job(job.id)
                if job_info:
                    jobs.append(job_info)

            return jobs
        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "list_jobs"},
                reraise=False
            )
            return []

    def run_job_now(self, job_id: str) -> bool:
        """立即运行任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功运行
        """
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                self.logger.warning(f"任务不存在: {job_id}")
                return False

            # 修改下次运行时间为现在
            job.modify(next_run_time=datetime.now())

            self.logger.info(f"立即运行任务: {job_id}")
            return True

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={"operation": "run_job_now", "job_id": job_id},
                reraise=False
            )
            return False

    def schedule_workflow(
        self,
        workflow_func: Callable,
        schedule_type: str = "cron",
        schedule_value: Union[str, int, datetime] = None,
        workflow_args: Optional[tuple] = None,
        workflow_kwargs: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None
    ) -> Optional[str]:
        """调度工作流任务

        Args:
            workflow_func: 工作流执行函数
            schedule_type: 调度类型 ('cron', 'interval', 'one_time')
            schedule_value: 调度值
                - cron: Cron表达式字符串，如 "0 2 * * *"
                - interval: 间隔秒数
                - one_time: 运行时间datetime对象
            workflow_args: 工作流函数位置参数
            workflow_kwargs: 工作流函数关键字参数
            job_id: 任务ID

        Returns:
            任务ID，如果调度失败返回None
        """
        try:
            if schedule_type == "cron":
                if not isinstance(schedule_value, str):
                    raise ValueError("Cron调度需要字符串类型的Cron表达式")
                return self.add_cron_job(
                    func=workflow_func,
                    cron_expression=schedule_value,
                    job_id=job_id,
                    args=workflow_args,
                    kwargs=workflow_kwargs
                )

            elif schedule_type == "interval":
                if not isinstance(schedule_value, (int, float)):
                    raise ValueError("间隔调度需要数字类型的秒数")
                return self.add_interval_job(
                    func=workflow_func,
                    interval_seconds=int(schedule_value),
                    job_id=job_id,
                    args=workflow_args,
                    kwargs=workflow_kwargs
                )

            elif schedule_type == "one_time":
                if not isinstance(schedule_value, datetime):
                    raise ValueError("一次性调度需要datetime类型的运行时间")
                return self.add_one_time_job(
                    func=workflow_func,
                    run_time=schedule_value,
                    job_id=job_id,
                    args=workflow_args,
                    kwargs=workflow_kwargs
                )

            else:
                raise ValueError(f"不支持的调度类型: {schedule_type}")

        except Exception as exc:
            self.exception_handler.handle_exception(
                exc,
                context={
                    "operation": "schedule_workflow",
                    "schedule_type": schedule_type,
                    "schedule_value": str(schedule_value),
                    "workflow_func": workflow_func.__name__
                },
                reraise=False
            )
            return None

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        jobs = self.list_jobs()

        return {
            "running": self.scheduler.running,
            "total_jobs": len(jobs),
            "active_jobs": len([j for j in jobs if not j.get("paused", False)]),
            "paused_jobs": len([j for j in jobs if j.get("paused", False)]),
            "next_run_time": min(
                [j["next_run_time"] for j in jobs if j.get("next_run_time")],
                default=None
            ),
        }


# 全局任务调度器实例
task_scheduler = TaskScheduler()

def get_task_scheduler() -> TaskScheduler:
    """获取全局任务调度器"""
    return task_scheduler


__all__ = [
    "TaskScheduler",
    "task_scheduler",
    "get_task_scheduler",
]