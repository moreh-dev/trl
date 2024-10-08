import os
import time
import mlflow
from transformers import TrainingArguments
from transformers.trainer_callback import TrainerCallback, TrainerControl, TrainerState

os.environ["DISABLE_MLFLOW_INTEGRATION"] = "False"
os.environ["HF_MLFLOW_LOG_ARTIFACTS"]="False"
os.environ["MLFLOW_FLATTEN_PARAMS"]="True"  

class TBTrainerCallback(TrainerCallback):
    "A callback log loss, learning rate, and throughput each logging step"
    start_time = time.time()
    epoch_start = 0

    def on_step_begin(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        # count the time after the logging step
        if state.global_step == 0 or state.global_step % args.logging_steps == 1:
            self.start_time = time.time()


    def on_log(self, args: TrainingArguments, state: TrainerState, control: TrainerControl,**kwargs):
        if args.logging_strategy == 'steps':
            logging_step_runtime = time.time() - self.start_time
            num_samples = args.per_device_train_batch_size * args.logging_steps
            throughput = num_samples / logging_step_runtime
            if 'loss' in state.log_history[-1]:
                state.log_history[-1]["throughput"] = throughput
                state.log_history[-1]["step"] = state.global_step
                state.log_history[-1]["step"] = state.global_step

                mlflow.log_metric("lr", state.log_history[-1]["learning_rate"] , step=state.global_step)
                mlflow.log_metric("throughput", throughput , step=state.global_step)
                mlflow.log_metric("train_loss", state.log_history[-1]["loss"] , step=state.global_step)
                print(f'loss: {state.log_history[-1]["loss"]}, lr: {state.log_history[-1]["learning_rate"]}, throughput: {throughput}, step: {state.global_step}')
            
    def on_epoch_end(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        all_loss_of_this_epoch = []
        for each in state.log_history[self.epoch_start:]:
            if 'loss' in each:
                all_loss_of_this_epoch.append(each['loss'])

        epoch_loss = sum(all_loss_of_this_epoch) / len(all_loss_of_this_epoch)
        mlflow.log_metric("epoch_loss", epoch_loss, step=int(state.epoch))

        self.epoch_start = len(state.log_history)


# Log number of parameters function
def get_num_parameters(model):
    num_params = 0
    for param in model.parameters():
        num_params += param.numel()
    # in million
                
                